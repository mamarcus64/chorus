# Sync

Once, so plain `ssh voices-aws` works. The Include line has to be first. An earlier `Host voices-aws` block wins, and a dead address makes `ssh` sit there with no output.

```bash
mkdir -p ~/.ssh && chmod 700 ~/.ssh
touch ~/.ssh/config && chmod 600 ~/.ssh/config
grep -v 'aws-connection/config' ~/.ssh/config > ~/.ssh/config.tmp
{ echo 'Include /data/mjma/chorus/aws-connection/config'; echo; cat ~/.ssh/config.tmp; } > ~/.ssh/config
rm ~/.ssh/config.tmp
```

Remote root is `/data/mjma/chorus`. `.env` is not in git. `CHORUS_PORT` on the instance must be `1945`.

## Code

```bash
cd /data/mjma/chorus/chorus && git push
ssh voices-aws 'cd /data/mjma/chorus/chorus && git pull'
```

If dependencies or the frontend changed, on the instance run `bash scripts/setup.sh`, then restart in tmux with `bash scripts/start.sh`.

## Stills

```bash
/data/mjma/chorus/data/sync.sh voices-aws
```

This reads the local database, sends every still those partitions use, and sends `manifest.json`. It does not send videos or the database.

## Labels

Annotate on the instance. Do not copy `voices.sqlite` onto a database that already has new rows.

```bash
/data/mjma/chorus/db/sync_db.sh voices-aws
```

This snapshots both databases, merges against `db/.base/voices.sqlite`, and writes the result back. It does not stop or start the app. A row changed on both sides stops the merge and writes `merge_report.json`. Apply the same migrations on both machines before this command.
