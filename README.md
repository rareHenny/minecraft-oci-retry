# Oracle Cloud free Minecraft server: automatic A1 capacity retries

This package retries an EXISTING Oracle Resource Manager stack named `Minecraft-Project-Infinity` every 10 minutes when the last Apply failed specifically due to Oracle's Ampere A1 capacity shortage.

It **does not** create any instance from scratch, change resource sizes, or modify your saved Terraform stack. It will stop if it encounters other errors, skip active jobs, and disable its GitHub Actions schedule once an Apply succeeds. It cannot guarantee capacity will appear.

## Before use

1. The existing Oracle stack must be named exactly `Minecraft-Project-Infinity` and live in region `eu-stockholm-1` (Stockholm).
2. The current last **Apply** job should be **FAILED** and its **Logs** should say `Out of capacity` / `Out of host capacity` for the A1 instance.
3. Review the saved stack: VM.Standard.A1.Flex, **2 OCPUs / 12 GB RAM total**, Ubuntu 24.04, **50 GB boot volume**, existing Minecraft-Network public subnet. Confirm no paid resources are present and keep your Oracle account on **Free Tier**, not Pay As You Go.
4. Don't delete or rename the stack while automation is running.

## GitHub repository (public code, no credentials)

Create a new GitHub repository (e.g. `minecraft-oci-retry`), with **Public** visibility for free standard hosted-runner minutes. Upload `retry_oci.py` to the repository root. Add the workflow file at `.github/workflows/retry.yml` using GitHub's *Add file > Create new file* dialog (typing the full path creates folders). Do not upload any `.pem`, OCI configuration, SSH keys, or `config` files.

## Generate a separate Oracle API signing key

In Oracle Console: user icon (top right) > **My profile** (or user details) > **API Keys** > **Add API Key** > **Generate API Key Pair**. Download the private key securely, then **Add** the corresponding public key in Oracle. In the generated configuration preview, find the `user`, `tenancy`, `fingerprint`, and `region` fields. This is an **API key**, not your Ubuntu SSH key. For stronger security, use a dedicated least-privilege Oracle identity with access only to the required stack and resources, rather than your tenancy administrator identity.

In GitHub, open repository **Settings > Secrets and variables > Actions > New repository secret**. Create these FIVE secrets:

| Secret | Value |
|---|---|
| `OCI_TENANCY_OCID` | The `tenancy=...` value from Oracle config preview |
| `OCI_USER_OCID` | The `user=...` value |
| `OCI_KEY_FINGERPRINT` | The `fingerprint=...` value |
| `OCI_API_PRIVATE_KEY` | The COMPLETE contents of the downloaded private API signing key PEM file, including BEGIN/END lines |
| `OCI_STACK_OCID` | The `ocid1.ormstack...` ID from Oracle **Resource Manager > Stacks > Minecraft-Project-Infinity > Stack details** |

Never paste your key into public repository files, chats, issues, or Actions logs. Never use your VM's SSH key as the OCI API signing key. You can revoke the Oracle API key when no longer needed.

## Activate and monitor

1. Open GitHub **Actions** > **Oracle Minecraft A1 capacity retry** > **Run workflow**, and confirm that the first run reports a new Apply job (or skips one already active).
2. The workflow then runs at minutes **07, 17, 27, 37, 47, and 57 UTC**, approximately every 10 minutes; GitHub may delay or skip individual scheduled runs.
3. Watch Oracle **Resource Manager > Jobs** and GitHub **Actions**. The job does not wait for a VM creation result: the next run checks it.
4. After an Apply job succeeds, the following workflow run disables this workflow through GitHub's API. Confirm your VM actually exists under **Compute > Instances** and is Running.
5. If a GitHub run fails for a non-capacity Oracle error, inspect the stack logs. Fix the issue before manually rerunning; the script deliberately refuses to spam unrelated errors.

## Important cost and safety details

- GitHub Actions on standard GitHub-hosted runners are free for public repositories. On **private repositories**, GitHub counts minutes against your allowance and may charge if you have enabled paid spending (depending on your plan/settings).
- Oracle **Free Trial** is not the same as Always Free. Re-check the entire saved Terraform stack and account type before permitting automatic Apply jobs. This script **cannot independently guarantee a Terraform stack is free**; it re-applies exactly what Oracle saved. It does not enforce cloud spending caps.
- GitHub secrets are encrypted but any workflow code with access to them is sensitive. Review every workflow change and use a dedicated narrowly-permissioned Oracle API identity wherever practical.
- GitHub can disable schedules on public repositories after 60 days with no repository activity; scheduled invocations are not guaranteed at an exact time.
- Once successfully launched, this automation stops; Minecraft still requires installing Java/Forge/modpack and configuring port 25565.

## References

- Oracle Apply jobs: https://docs.oracle.com/en-us/iaas/Content/ResourceManager/Tasks/create-job-apply.htm
- Oracle API signing key: https://docs.oracle.com/en-us/iaas/Content/Identity/access/to_upload_an_API_signing_key.htm
- GitHub scheduled workflows: https://docs.github.com/en/actions/reference/events-that-trigger-workflows#schedule
- GitHub billing: https://docs.github.com/en/billing/concepts/product-billing/github-actions
