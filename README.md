
![Sign World Model](MAPCORE.png "Title")


**map-core** is an open source library that allows building a semiotic network
based on the principles of the sign world model. 
The [swm part](src/swm/README.md) is responsible for the description and creation of the basic 
elements of the world model - signs, causal matrices, connectors 
between matrices, events, etc. The [planning part](src/planning/README.md) implements the basic principles 
of the case-based planning and allows to build hierarchical plans in 
a single-agent system. The part related to [reasoning](src/reasoning) will describe the basic 
principles of replenishing the world model in the process of reasoning of an agent.

## Installation

To install the current release:

```
>>>python3 setup.py sdist
>>>python3 setup.py install
```

