nohup locust -f locustfile.py --host=https://vulnbank.mytechlab.my.id --headless --users 50 --spawn-rate 5 --run-time 3d > locust.log 2>&1 &


Start logrotate setup **first**, before running Locust. That way the rotation is already watching the file from the moment it gets created.

**Step 1 — Create the logrotate config:**
```bash
sudo nano /etc/logrotate.d/locust
```

Paste this (update the path to match where your `locust.log` will be):
```
/home/shaugi/locust.log {
    size 100M
    rotate 3
    compress
    missingok
    notifempty
    copytruncate
}
```

**Step 2 — Test the config is valid:**
```bash
sudo logrotate -d /etc/logrotate.d/locust
```
You'll see a dry-run output — no actual rotation happens, just confirms no syntax errors.

**Step 3 — Start Locust:**
```bash
nohup locust -f locustfile.py \
  --host=https://vulnbank.mytechlab.my.id \
  --headless --users 50 --spawn-rate 5 --run-time 3d \
  > locust.log 2>&1 &
```

**Step 4 — Confirm it's running:**
```bash
ps aux | grep locust
tail -f locust.log
```

---

That's it. `logrotate` runs automatically every day via cron, so once the config is in place you don't need to touch it again. With 50 users over 3 days, `100M` per file and 3 rotations gives you up to 300MB max before old logs get deleted.