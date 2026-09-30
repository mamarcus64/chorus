# Chorus

Annotation site for more than one project. The first project is `voices`.

Three folders sit next to each other. This repository is only the code.

```
/data/mjma/chorus/
  chorus/     git: app, task modules, migrations, builders
  db/         one SQLite file per project, plus merge and backup scripts
  data/       raw files, manifest.json, and the rsync script
```

The running app only reads files on its own machine. Moving to another host is a file copy: git for this repo, rsync for `data/`, and a row merge for `db/`.

## Setup

```bash
cp .env.example .env    # set CHORUS_SECRET_KEY and CHORUS_REGISTRATION_KEY
bash scripts/setup.sh
bash scripts/start.sh
```

Open http://localhost:8733 . The site redirects to `/p/voices`.

`setup.sh` creates a conda env named `chorus` (Python 3.12 and Node), installs this package, builds the frontend, applies migrations, and links the operator scripts into `../db` and `../data`.

## Accounts

Registration asks for the registration key from `.env`. Passwords are stored as argon2 hashes. The session is a signed cookie.

Admin is not granted by the site. Set it in the database:

```bash
sqlite3 ../db/voices.sqlite \
  "UPDATE users SET is_admin=1, updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE username='ada';"
```

## Work model

A **task** is a code module (`frame_choice` is the first), named by a row in the project database. A **partition** is one batch of **items**. Items point at raw files through `data/<project>/manifest.json`. Labels live in `annotations`, separate from the media.

The home page lists partitions as To-do, Not assigned, or Done.

- New partitions are assigned to everyone, so they start on To-do.
- An admin can switch a partition to a named set of people. Everyone else still sees it, under Not assigned.
- A person who registers later is not added to a selected list.
- The partition moves to Done when every item has an answer, or when the person presses Mark done.
- Reopen puts it back on To-do and keeps the answers. The next save is what can mark it Done again.

## First VOICES task

Frames with Py-Feat `FaceScore > 0.9`. The question is whether a human head is inside the drawn box. Answers are Yes, No, or Unsure.

```bash
python projects/voices/build_head_present.py \
  --partition-name pilot-100 --n 100 --seed 1 --min-score 0.9 --sources usc,yale
```

Stills are rendered on this machine with OpenCV (the decoder Py-Feat used) and stored under `data/voices/stills/`. Sync copies those files, not the whole video collection.

```bash
python -m chorus files --project voices --partition all > /tmp/chorus-files.txt
../data/sync.sh user@host:/data/mjma/chorus/data/voices /tmp/chorus-files.txt
```

## Database merge

Do not copy `voices.sqlite` over a database that has new labels. Checkpoint both copies and merge them against the last shared base:

```bash
../db/merge.py ../db/.base/voices.sqlite ../db/voices.sqlite /tmp/remote.sqlite -o /tmp/merged.sqlite
```

A row changed on only one side is kept. A row changed on both sides stops the merge. `--prefer newer` keeps the later `updated_at`. The same username registered on both machines is reported and not applied.

`../db/sync_db.sh user@host` pulls the remote file, merges, and pushes the result. `../db/backup.sh` writes a snapshot with SQLite's `.backup`.

On the first deploy, copy the database you sent to the host into `db/.base/voices.sqlite` before the first merge.

## Tests

```bash
conda activate chorus
pytest
python projects/voices/frame_check.py
```
