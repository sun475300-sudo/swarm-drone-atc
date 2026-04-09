cd /d "C:\Users\sun47\Desktop\swarm-drone-atc"
echo === REFLOG === > git_recover.log
git reflog >> git_recover.log 2>&1
echo === FSCK DANGLING === >> git_recover.log
git fsck --lost-found --no-reflogs >> git_recover.log 2>&1
echo === DONE === >> git_recover.log
