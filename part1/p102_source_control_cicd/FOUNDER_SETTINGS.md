# Settings only the Founder can switch on

Package P1.02 built the review rules as code. Turning them on is an account setting, and only the Founder may
change one (rule 4). None of these needs a credential, and nothing here asks you to reveal one.

Until these are on, the guard still runs in the pipeline and will show a red mark, but GitHub will not stop
anyone from merging past it. **The rules exist. These settings give them teeth.**

## 1. Branch protection on `main`

GitHub, repository **Settings**, then **Branches**, then **Add branch ruleset** (or **Add rule**) for `main`:

| Setting | Value | Why |
| --- | --- | --- |
| Require a pull request before merging | on | A change reaches main only after review (P1.02 Done when) |
| Required approvals | 1 | Rule 2: the builder never approves its own work |
| Dismiss stale approvals when new commits are pushed | on | An approval binds to what was reviewed, not to what came after |
| Require review from Code Owners | on | `.github/CODEOWNERS` decides who reviews which folder |
| Require status checks to pass | on, and select **check** | The ownership guard and the contract tests must pass |
| Require branches to be up to date before merging | on | The checks ran against what will actually land |
| Do not allow bypassing the above settings | on | Including for an administrator. Otherwise rule W2 is a suggestion |
| Allow force pushes | off | History is evidence (AMD-3) |
| Allow deletions | off | |

## 2. Keep the repository private

**Settings**, then **General**, then **Danger Zone**: the repository must stay **Private** (LA-SEC-06).

## 3. Actions permissions

**Settings**, then **Actions**, then **General**:

| Setting | Value | Why |
| --- | --- | --- |
| Workflow permissions | Read repository contents | The pipeline builds and tests. It never writes back |
| Allow GitHub Actions to create and approve pull requests | off | An Action must never approve work |

## 4. One thing to check, not to set

Open **Actions** after the first push and confirm the run named **Dyson Layer A** is green. It runs the
ownership guard, the 58 contract tests, builds the artifact, and proves the artifact rebuilds to the same
bytes.

## What stays off on purpose

No deploy key, no self-hosted runner, no Action that can reach AWS, and no webhook into the runtime. GitHub is
source control and CI/CD only; it is never the scheduler or the command bus (LA-SEC-06). When a deployment to
AWS is built in 2A.01, the Founder approves the credential path separately, and it does not live here.
