# zuleyha
a simple web application to watch how's it going with computers that are registered

To run (at least in a virtualenv - which is what I always do) 

```
cd zuleyha #(which is the project root)
virtualenv venv
. venv/bin/activate
cd zuleyha # (now it should be zuleyha/zuleyha)
export FLASK_APP=zuleyha
flask register --hostname <host_name> --username <user_name>
flask run
```

This initial version only runs locally and I only tested it with virtualenv. 
It also only reports average load (via /proc/loadavg) and top 5 cpu hungry processes.
It is unknown whether I'll continue working on this or not. 
