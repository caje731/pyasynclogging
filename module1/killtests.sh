for pid in `ps -ef | grep "python test.py" | cut -f 3 -d ' '`
do
kill -9 $pid
done