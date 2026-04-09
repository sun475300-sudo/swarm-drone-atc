cd /d "C:\Users\sun47\Desktop\swarm-drone-atc"
git add -A > push_restore.log 2>&1
git commit -m "restore: recover all files from commit 2349865" >> push_restore.log 2>&1
git push origin main >> push_restore.log 2>&1
echo === DONE === >> push_restore.log
