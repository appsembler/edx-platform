# Requirement management for Tahoe
This readme shows how to add or override an Open edX requirement.

# Objective

 - Make it obvious which requirements are we managing without needing to use `git diff`.
 - Keep all overrides in a single file: `appsembler.txt` (with minor exceptions such as `Django`).
 - Easier release upgrades by having simpler `git merge`.

## Base requirements
This includes all pip packages that Tahoe won't work without it, including `tahoe-sites`, `sentry-sdk` and upstream overrides. In other words, if a package is required in testing, add it to `appsembler.txt` file.

### Add a requirement
Add an entry in the `appsembler.txt` file.

### Override an upstream requirement
Go to the `requirement/edx/*.txt` files and comment the line with `# appsembler.txt:` prefix:

```diff
-analytics-python==1.2.9
+# appsembler.txt: analytics-python==1.2.9
```

Add the new overriding requirement into `appsembler.txt` file. Preferably with a comment and a Jira ticket reference:

```
+analytics-python==1.4.0  # RED-2969: To enable sync_mode
```

### Additional production-only requirements
Tahoe relies on additional packages to run in production like `Figures`, `xblock-grade-fetcher` and
`xblock-problem-builder` but not required in during testing.

These packages are added into both `edx-platform:Dockerfile.tutor` and `edx-configs` `server-vars.yml` files.
