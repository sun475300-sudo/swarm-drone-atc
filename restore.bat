cd /d "C:\Users\sun47\Desktop\swarm-drone-atc"
echo === Restoring files from commit 2349865 === > restore.log
git checkout 2349865 -- . >> restore.log 2>&1
echo === Status after restore === >> restore.log
git status --short >> restore.log 2>&1
echo === DONE === >> restore.log
