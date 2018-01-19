# farsiscript
JavaScript parser dialected in Farsi. The goal is made javascript programming easy for iranian.
This library is based on PyJsParser (https://github.com/PiotrDabkowski/pyjsparser) parser by PiotrDabkowski.


# Installation 

    pip install farsiscript
    
# Example
    
    >>> from farsiscript import PyJsParser
    >>> p = PyJsParser()
    >>> p.parse('motaghayer $ = "Hello!"')
    {
    "type": "Program",
    "body": [
        {
            "type": "VariableDeclaration",
            "declarations": [
                {
                    "type": "VariableDeclarator",
                    "id": {
                        "type": "Identifier",
                        "name": "$"
                    },
                    "init": {
                        "type": "Literal",
                        "value": "Hello!",
                        "raw": '"Hello!"'
                    }
                }
            ],
            "kind": "motaghayer"
        }
      ]
    }
