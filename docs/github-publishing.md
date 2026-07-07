# GitHub Publishing

The repository target is `jhxu003/BadmintonCoachSkill`.

## Token Rule

Do not use any token that has been pasted into chat or logs. Generate a fresh fine-grained token for publishing.

Minimum permissions:

- Metadata: read-only.
- Contents: read and write.
- Administration: read and write only if the agent must create the repository.

## Safe Flow

1. Store the fresh token in an environment variable only for the current shell.
2. Create the private repository through the GitHub API if needed.
3. Push using a temporary credential path.
4. Reset `origin` to `https://github.com/jhxu003/BadmintonCoachSkill.git`.
5. Verify `git remote -v` contains no token.
6. Revoke the temporary token after publishing.

## Fallback

If no fresh token is available, keep the local commit ready and ask the user to create an empty private repository in the browser.

