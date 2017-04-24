# zuleyha
a simple web application to watch how's it going with computers that are registered
(why not SNMP? well, i made this for fun.)

It requres python3, jinja2.

To run, first you should register some slave machines. 


e.g.:
```
python zuleyha.py -r localhost ugurkoltuk
```

to run,


```
python zuleyha.py
```

It is unknown whether I'll continue working on this or not.

KNOWN ISSUES:
cpu percentage that's printed comes from ps, it is not "how many percent of the CPU is 
used by the process" but rather "how many percent of its lifetime was spent using CPU by this process"
I will (maybe) fix it.
