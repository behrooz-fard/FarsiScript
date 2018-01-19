# farsiscript
JavaScript parser dialected in Farsi. The goal is made javascript programming easy for iranian.
This library is based on PyJsParser (https://github.com/PiotrDabkowski/pyjsparser) parser by PiotrDabkowski.


# Installation 

    pip install farsiscript

# FarsiScript substitutes for JavaScript commands

    | JavaScript    | FarsiScript   |
    | ------------- | ------------- |
    | break         | bebor         |
    | case          | mored         |
    | catch         | begir         |
    | continue      | edame         |
    | debugger      | eshkalzodaee  |
    | default       | pishfarz      |
    | do            | anjambede     |
    | else          | varna         |
    | finally       | darnahayat    |
    | for           | baraye        |
    | function      | tabe          |
    | if            | agar          |
    | in            | dar           |
    | new           | jadid         |
    | return        | bazgardan     |
    | switch        | bargozin      |
    | throw         | partkon       |
    | try           | bekoosh       |
    | var           | motaghayer    |
    | while         | tavaghti      |

# Example
    
    >>> from farsiscript import FsParser
    >>> p = FsParser()
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
