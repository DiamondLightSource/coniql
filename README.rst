coniql
======

Control system interface in GraphQL

Installation
------------

After cloning from Github/Gitlab, install epics base in /scratch from:

https://epics-controls.org/download/base/base-7.0.2.2.tar.gz

cd to the directory and type make

Then install the depenencies using instructions from:

https://confluence.diamond.ac.uk/display/SSCC/Python+3+User+Documentation

Then you can run the example::
    
    PYTHONPATH=. pipenv run python coniql/server.py

And see the grphiql interface here:

http://localhost:8000/graphiql

For instance:

http://localhost:8000/graphiql?query=%23%20Welcome%20to%20GraphiQL%0A%23%0A%23%20GraphiQL%20is%20an%20in-browser%20tool%20for%20writing%2C%20validating%2C%20and%0A%23%20testing%20GraphQL%20queries.%0A%23%0A%23%20Type%20queries%20into%20this%20side%20of%20the%20screen%2C%20and%20you%20will%20see%20intelligent%0A%23%20typeaheads%20aware%20of%20the%20current%20GraphQL%20type%20schema%20and%20live%20syntax%20and%0A%23%20validation%20errors%20highlighted%20within%20the%20text.%0A%23%0A%23%20GraphQL%20queries%20typically%20start%20with%20a%20%22%7B%22%20character.%20Lines%20that%20starts%0A%23%20with%20a%20%23%20are%20ignored.%0A%23%0A%23%20An%20example%20GraphQL%20query%20might%20look%20like%3A%0A%23%0A%23%20%20%20%20%20%7B%0A%23%20%20%20%20%20%20%20field(arg%3A%20%22value%22)%20%7B%0A%23%20%20%20%20%20%20%20%20%20subField%0A%23%20%20%20%20%20%20%20%7D%0A%23%20%20%20%20%20%7D%0A%23%0A%23%20Keyboard%20shortcuts%3A%0A%23%0A%23%20%20%20%20%20%20%20Run%20Query%3A%20%20Ctrl-Enter%20(or%20press%20the%20play%20button%20above)%0A%23%0A%23%20%20%20Auto%20Complete%3A%20%20Ctrl-Space%20(or%20just%20start%20typing)%0A%23%0A%0Asubscription%20%7B%0A%20%20subscribeFloatScalar(channel%3A%20%22TMC43-TS-IOC-01%3AAI%22)%20%7B%0A%20%20%20%20typeid%0A%20%20%20%20value%0A%20%20%20%20timeStamp%20%7B%0A%20%20%20%20%20%20secondsPastEpoch%0A%20%20%20%20%20%20nanoseconds%0A%20%20%20%20%7D%0A%20%20%20%20alarm%20%7B%0A%20%20%20%20%20%20severity%0A%20%20%20%20%20%20status%0A%20%20%20%20%20%20message%0A%20%20%20%20%7D%0A%20%20%7D%0A%7D


    

