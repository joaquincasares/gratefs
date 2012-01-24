GrateFS
-------

A grate and easy alternative to other grid based file-systems.

This version of GrateFS is merely an API to expand on. Currently it wraps DataStax Enterprise commands with a Python subprocess to the shell and easily handles:

* transfers,
* file inspection,
* location memory,
* remote access, and
* pipes.

Benefits
========

With this project there is:

* an easy to use command line tool,
* an easy to use command line interface, and
* an easy to use Python API for easy implementation in your current codebase.

Also, due to Apache Cassandra's innate view of datacenters and replication, no further code is needed to allow for cross datacenter replication. Simply setup your strategy_options for your `cfs` keyspace through your `cassandra-cli` to represent where you wish your data to be stored.

DataStax Enterprise does all this easily and efficiently due to it's model of Apache Hadoop built on top of Apache Cassandra.

Usage
=====

A complete view of GrateFS's usage is as follows:

    # Command line interface
        cli
    
    # File access
        put <local_src> ... <dst>
        get <src> <local_dst>
        delete|rm <src> ...

    # Inspection
        list|ls [dst]
        exists <src> ...
        cat <src> ...
        tail <src> ...

    # Movement
        mkdir <dst>
        rmdir <dst>
        cd [dst]
        pwd

    # Remote access
        remote <host>:<port>
        local

    # Pipe access
        pipe <dst>
        openpipe <dst>
        merge <dst> <local_dst>

Pipes
=====

Due to the nature of this code, all piped information is written out to Python tempfiles, pushed to the DSE cluster, and then removed.

The `pipe` command will temporarily require as much diskspace as the initial stdin read can take and be pushed once.

The `openpipe` command will parse the input into 8192 byte chunks from stdin and continue pushing the chunks to the cluster under the specified folder. GrateFS will continue to push the chunks to the server until it reads no more data, at that point, it will continue to cycle waiting for more data from stdin. A `ctrl-c` will kill the piping process. Later, a `merge` command will merge all the chunks into a local file on your machine.

Sample Run (Command Line Tool)
==============================
    host1:~/gratefs$ ls
    accountImage1.jpg  gratefs  gratefs.py  rbranson.pem  README.md  zznate.pem
    host1:~/gratefs$ ./gratefs ls
    Found 1 items
    drwxrwxrwx   - cassandra cassandra          0 2012-01-20 22:00 /tmp
    host1:~/gratefs$ ./gratefs put accountImage1.jpg .
    host1:~/gratefs$ ./gratefs mkdir pem_files
    host1:~/gratefs$ ./gratefs cd pem_files
    host1:~/gratefs$ ./gratefs put zznate.pem .
    host1:~/gratefs$ ./gratefs put rbranson.pem /pem_files/rbranson.pem
    host1:~/gratefs$ ./gratefs ls
    Found 2 items
    -rwxrwxrwx   1 ubuntu ubuntu       1694 2012-01-20 22:06 /pem_files/rbranson.pem
    -rwxrwxrwx   1 ubuntu ubuntu       1692 2012-01-20 22:06 /pem_files/zznate.pem

Sample Run (Command Line Interface)
===================================

    host1:~/gratefs$ ./gratefs cli
    [grateFS] get rbranson.pem .
    get: Target ./rbranson.pem already exists
    [grateFS] get rbranson.pem rbranson.pem.bak
    [grateFS] get zznate.pem zznate.pem.bak
    [grateFS] cd
    [grateFS] ls
    Found 3 items
    -rwxrwxrwx   1 ubuntu    ubuntu         14640 2012-01-20 22:04 /accountImage1.jpg
    drwxrwxrwx   - cassandra cassandra          0 2012-01-20 22:00 /tmp
    drwxrwxrwx   - ubuntu    ubuntu             0 2012-01-20 22:05 /pem_files
    [grateFS] get /accountImage1.jpg accountImage1.jpg.bak
    [grateFS] exit

    host1:~/gratefs$ md5sum *
    1b51a397a6edcba81d06a71fb563d7a9  accountImage1.jpg
    1b51a397a6edcba81d06a71fb563d7a9  accountImage1.jpg.bak
    ...
    092d1ceb692aab6bf5aa737feb3c7b14  rbranson.pem
    092d1ceb692aab6bf5aa737feb3c7b14  rbranson.pem.bak
    3d78a089ccb22ee720ba064636d5ac25  zznate.pem
    3d78a089ccb22ee720ba064636d5ac25  zznate.pem.bak

Sample Run (Pipes)
==================

    host1:~/gratefs$ cat zznate.pem | ./gratefs pipe piped.pem
    host1:~/gratefs$ cat accountImage1.jpg | ./gratefs openpipe open_piped.jpg
    ^Chost1:~/gratefs./gratefs ls
    Found 5 items
    -rwxrwxrwx   1 ubuntu    ubuntu         14640 2012-01-20 22:04 /accountImage1.jpg
    drwxrwxrwx   - cassandra cassandra          0 2012-01-20 22:00 /tmp
    drwxrwxrwx   - ubuntu    ubuntu             0 2012-01-20 22:17 /open_piped.jpg
    drwxrwxrwx   - ubuntu    ubuntu             0 2012-01-20 22:05 /pem_files
    -rwxrwxrwx   1 ubuntu    ubuntu          1692 2012-01-20 22:15 /piped.pem
    host1:~/gratefs$ ./gratefs ls /open_piped.jpg
    Found 2 items
    -rwxrwxrwx   1 ubuntu ubuntu       6448 2012-01-20 22:17 /open_piped.jpg/part-0000000001
    -rwxrwxrwx   1 ubuntu ubuntu       8192 2012-01-20 22:17 /open_piped.jpg/part-0000000000
    host1:~/gratefs$ ./gratefs get piped.pem zznate.pem.bak2
    host1:~/gratefs$ ./gratefs merge open_piped.jpg accountImage1.jpg.bak2

    host1:~/gratefs$ md5sum *
    1b51a397a6edcba81d06a71fb563d7a9  accountImage1.jpg
    1b51a397a6edcba81d06a71fb563d7a9  accountImage1.jpg.bak
    1b51a397a6edcba81d06a71fb563d7a9  accountImage1.jpg.bak2
    ...
    3d78a089ccb22ee720ba064636d5ac25  zznate.pem
    3d78a089ccb22ee720ba064636d5ac25  zznate.pem.bak
    3d78a089ccb22ee720ba064636d5ac25  zznate.pem.bak2

Known Errors
============

Getting a:
    
    java.io.FileNotFoundException: /Users/joaquin/repos/bdp/logs/hadoop/SecurityAuth.audit (Permission denied)
    ...

Run GrateFS as sudo.
