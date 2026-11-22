"""Safely retry ONE already-configured Oracle Resource Manager stack.

This script intentionally does not launch instances directly or edit the stack.
It only creates a new APPLY job after confirming that the most recent failed
APPLY job failed due to capacity. It stops after ANY successful APPLY job.
"""

import os
import sys

import oci


STACK_NAME = "Minecraft-Project-Infinity"
REGION = "eu-stockholm-1"
ACTIVE_STATES = {"ACCEPTED", "IN_PROGRESS", "CANCELING"}
CAPACITY_INDICATORS = (
    "out of capacity",
    "out of host capacity",
    "outofhostcapacity",
    "capacity not available",
    "out of capacity for shape",
)


def required(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing GitHub secret: {name}")
    return value


def main():
    stack_id = required("OCI_STACK_OCID")
    if not stack_id.startswith("ocid1.ormstack."):
        raise RuntimeError("OCI_STACK_OCID does not look like a Resource Manager stack OCID")

    api_key = required("OCI_API_PRIVATE_KEY").replace("\\n", "\n")
    signer = oci.signer.Signer(
        tenancy=required("OCI_TENANCY_OCID"),
        user=required("OCI_USER_OCID"),
        fingerprint=required("OCI_KEY_FINGERPRINT"),
        private_key_file_location=None,
        private_key_content=api_key,
    )
    # OCI validates the client config even when an API-key Signer is supplied.
    # Use key_content instead of writing the private key to disk.
    client_config = {
        "region": REGION,
        "tenancy": required("OCI_TENANCY_OCID"),
        "user": required("OCI_USER_OCID"),
        "fingerprint": required("OCI_KEY_FINGERPRINT"),
        "key_content": api_key,
    }
    client = oci.resource_manager.ResourceManagerClient(client_config, signer=signer)

    stack = client.get_stack(stack_id).data
    if stack.display_name != STACK_NAME:
        raise RuntimeError(
            f"Refusing to apply stack named {stack.display_name!r}; "
            f"expected {STACK_NAME!r}."
        )
    if stack.lifecycle_state != "ACTIVE":
        raise RuntimeError(f"Stack is not ACTIVE (state={stack.lifecycle_state!r}).")

    jobs = oci.pagination.list_call_get_all_results(
        client.list_jobs,
        stack_id=stack_id,
        sort_by="TIMECREATED",
        sort_order="DESC",
    ).data
    apply_jobs = sorted(
        (job for job in jobs if job.operation == "APPLY"),
        key=lambda job: job.time_created,
        reverse=True,
    )

    if any(job.lifecycle_state == "SUCCEEDED" for job in apply_jobs):
        print("SUCCESS: a previous APPLY job succeeded. No further VM creation attempts.")
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
            output.write("deployed=true\n")
        return

    if any(job.lifecycle_state in ACTIVE_STATES for job in jobs):
        print("Another Oracle Resource Manager job is active. Skipping this interval.")
        return

    if not apply_jobs:
        raise RuntimeError(
            "No previous APPLY job found. First attempt Apply manually in Oracle and "
            "confirm the error is only an ARM capacity shortage."
        )

    latest = apply_jobs[0]
    if latest.lifecycle_state != "FAILED":
        raise RuntimeError(
            f"Last APPLY job is {latest.lifecycle_state!r}, not FAILED. "
            "Refusing to submit another automatically."
        )

    logs = str(client.get_job_logs_content(latest.id).data).lower()
    if not any(indicator in logs for indicator in CAPACITY_INDICATORS):
        raise RuntimeError(
            "Previous APPLY job did not show a recognized capacity error. "
            "Check its logs in the Oracle console; automation is stopping safely."
        )

    details = oci.resource_manager.models.CreateJobDetails(
        stack_id=stack_id,
        display_name="Minecraft-A1-capacity-retry",
        operation="APPLY",
        job_operation_details=oci.resource_manager.models.CreateApplyJobOperationDetails(
            execution_plan_strategy="AUTO_APPROVED"
        ),
    )
    result = client.create_job(details).data
    print(f"Submitted a new Resource Manager APPLY job. State: {result.lifecycle_state}")
    print("The next scheduled run will inspect its result. No parallel job is started.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Avoid dumping tracebacks/HTTP request data into public GitHub Actions logs.
        print(f"Stopped: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
