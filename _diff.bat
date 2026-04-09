cd /d C:\Users\sun47\Desktop\swarm-drone-atc
echo === origin/main vs local main === > diff_check.log 2>&1
git log --oneline origin/main -5 >> diff_check.log 2>&1
echo. >> diff_check.log
echo === origin/master (files only in master, not in main) === >> diff_check.log
git diff --stat main origin/master >> diff_check.log 2>&1
echo. >> diff_check.log
echo === origin/presentation/portfolio vs main === >> diff_check.log
git diff --stat main origin/presentation/portfolio >> diff_check.log 2>&1
echo. >> diff_check.log
echo === File counts per branch === >> diff_check.log
echo main: >> diff_check.log
git ls-tree -r main --name-only 2>nul | find /c /v "" >> diff_check.log 2>&1
echo master: >> diff_check.log
git ls-tree -r origin/master --name-only 2>nul | find /c /v "" >> diff_check.log 2>&1
echo presentation/portfolio: >> diff_check.log
git ls-tree -r origin/presentation/portfolio --name-only 2>nul | find /c /v "" >> diff_check.log 2>&1
echo DONE >> diff_check.log
