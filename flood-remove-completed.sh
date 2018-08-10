REMOTE="https://tv.lastpengu.in/RPC2 -username admin -password 2114"

for torrentid in $(xmlrpc $REMOTE download_list "" | grep -o "'.*'" | sed "s/'//g"); do
    echo "Processing torrent $torrentid";

    xmlrpc $REMOTE d.complete "$torrentid" | grep "1" > /dev/null 2>&1 ;

    if [ $? = 0 ]; then
        echo "\tcompleted";
        xmlrpc $REMOTE d.erase "$torrentid";
        COMPLETED_ANY=1
    else
        echo "\tin progress";
    fi
done
