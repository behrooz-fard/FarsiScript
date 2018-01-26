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

# Example 1
    
    >>> from farsiscript import FsParser
    >>> p = FsParser()
    >>> p.parse('motaghayer $ = "SALAM!"')
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


# Example 2

    >>> from farsiscript import FsParser
    >>> p = FsParser()
    >>> p.parse('motaghayer greeting;'
              'motaghayer time = jadid Date().getHours();'
              'agar (time < 10) {greeting = "Good morning";'
              '} varna agar (time < 20) {greeting = "Good day";'
              '} varna {greeting = "Good evening";'
              '}')
        {
        'body': [
        {
          'declarations': [
            {
              'init': None,
              'id': {
                'name': 'greeting',
                'type': 'Identifier'
              },
              'type': 'VariableDeclarator'
            }
          ],
          'type': 'VariableDeclaration',
          'kind': 'motaghayer'
        },
        {
          'declarations': [
            {
              'init': {
                'callee': {
                  'property': {
                    'name': 'getHours',
                    'type': 'Identifier'
                  },
                  'object': {
                    'callee': {
                      'name': 'Date',
                      'type': 'Identifier'
                    },
                    'arguments': [

                    ],
                    'type': 'NewExpression'
                  },
                  'type': 'MemberExpression',
                  'computed': False
                },
                'arguments': [

                ],
                'type': 'CallExpression'
              },
              'id': {
                'name': 'time',
                'type': 'Identifier'
              },
              'type': 'VariableDeclarator'
            }
          ],
          'type': 'VariableDeclaration',
          'kind': 'motaghayer'
        },
        {
          'test': {
            'left': {
              'name': 'time',
              'type': 'Identifier'
            },
            'right': {
              'raw': None,
              'type': 'Literal',
              'value': 10.0
            },
            'operator': '<',
            'type': 'BinaryExpression'
          },
          'alternate': {
            'test': {
              'left': {
                'name': 'time',
                'type': 'Identifier'
              },
              'right': {
                'raw': None,
                'type': 'Literal',
                'value': 20.0
              },
              'operator': '<',
              'type': 'BinaryExpression'
            },
            'alternate': {
              'body': [
                {
                  'expression': {
                    'left': {
                      'name': 'greeting',
                      'type': 'Identifier'
                    },
                    'right': {
                      'raw': None,
                      'type': 'Literal',
                      'value': 'Good evening'
                    },
                    'operator': '=',
                    'type': 'AssignmentExpression'
                  },
                  'type': 'ExpressionStatement'
                }
              ],
              'type': 'BlockStatement'
            },
            'consequent': {
              'body': [
                {
                  'expression': {
                    'left': {
                      'name': 'greeting',
                      'type': 'Identifier'
                    },
                    'right': {
                      'raw': None,
                      'type': 'Literal',
                      'value': 'Good day'
                    },
                    'operator': '=',
                    'type': 'AssignmentExpression'
                  },
                  'type': 'ExpressionStatement'
                }
              ],
              'type': 'BlockStatement'
            },
            'type': 'IfStatement'
          },
          'consequent': {
            'body': [
              {
                'expression': {
                  'left': {
                    'name': 'greeting',
                    'type': 'Identifier'
                  },
                  'right': {
                    'raw': None,
                    'type': 'Literal',
                    'value': 'Good morning'
                  },
                  'operator': '=',
                  'type': 'AssignmentExpression'
                },
                'type': 'ExpressionStatement'
              }
            ],
            'type': 'BlockStatement'
          },
          'type': 'IfStatement'
        },
        {
          'type': 'EmptyStatement'
        }
      ],
      'type': 'Program'
    }


# Example 3

    >>> from farsiscript import FsParser
    >>> p = FsParser()
    >>> p.parse('motaghayer person = {fname:"John", lname:"Doe", age:25};'
              'motaghayer text = "";'
              'motaghayer x;'
              'baraye (x dar person) {'
              '    text += person[x] + " ";'
              ' }')
        {
        'body': [
        {
          'declarations': [
            {
              'init': {
                'properties': [
                  {
                    'method': False,
                    'computed': False,
                    'type': 'Property',
                    'shorthand': False,
                    'kind': 'init',
                    'value': {
                      'raw': None,
                      'value': 'John',
                      'type': 'Literal'
                    },
                    'key': {
                      'name': 'fname',
                      'type': 'Identifier'
                    }
                  },
                  {
                    'method': False,
                    'computed': False,
                    'type': 'Property',
                    'shorthand': False,
                    'kind': 'init',
                    'value': {
                      'raw': None,
                      'value': 'Doe',
                      'type': 'Literal'
                    },
                    'key': {
                      'name': 'lname',
                      'type': 'Identifier'
                    }
                  },
                  {
                    'method': False,
                    'computed': False,
                    'type': 'Property',
                    'shorthand': False,
                    'kind': 'init',
                    'value': {
                      'raw': None,
                      'value': 25.0,
                      'type': 'Literal'
                    },
                    'key': {
                      'name': 'age',
                      'type': 'Identifier'
                    }
                  }
                ],
                'type': 'ObjectExpression'
              },
              'type': 'VariableDeclarator',
              'id': {
                'name': 'person',
                'type': 'Identifier'
              }
            }
          ],
          'kind': 'motaghayer',
          'type': 'VariableDeclaration'
        },
        {
          'declarations': [
            {
              'init': {
                'raw': None,
                'value': '',
                'type': 'Literal'
              },
              'type': 'VariableDeclarator',
              'id': {
                'name': 'text',
                'type': 'Identifier'
              }
            }
          ],
          'kind': 'motaghayer',
          'type': 'VariableDeclaration'
        },
        {
          'declarations': [
            {
              'init': None,
              'type': 'VariableDeclarator',
              'id': {
                'name': 'x',
                'type': 'Identifier'
              }
            }
          ],
          'kind': 'motaghayer',
          'type': 'VariableDeclaration'
        },
        {
          'each': False,
          'body': {
            'body': [
              {
                'expression': {
                  'operator': '+=',
                  'left': {
                    'name': 'text',
                    'type': 'Identifier'
                  },
                  'right': {
                    'operator': '+',
                    'left': {
                      'property': {
                        'name': 'x',
                        'type': 'Identifier'
                      },
                      'computed': True,
                      'object': {
                        'name': 'person',
                        'type': 'Identifier'
                      },
                      'type': 'MemberExpression'
                    },
                    'right': {
                      'raw': None,
                      'value': ' ',
                      'type': 'Literal'
                    },
                    'type': 'BinaryExpression'
                  },
                  'type': 'AssignmentExpression'
                },
                'type': 'ExpressionStatement'
              }
            ],
            'type': 'BlockStatement'
          },
          'left': {
            'name': 'x',
            'type': 'Identifier'
          },
          'right': {
            'name': 'person',
            'type': 'Identifier'
          },
          'type': 'ForInStatement'
        },
        {
          'type': 'EmptyStatement'
        }
      ],
      'type': 'Program'
    }

# Example 4

    >>> from farsiscript import FsParser
    >>> p = FsParser()
    >>> p.parse('bargozin (jadid Date().getDay()) {'
              '    mored 0:'
              '        day = "Sunday";'
              '        bebor;'
              '    mored 1:'
              '        day = "Saturday";'
              '        bebor;'
              '    pishfarz:'
              '        day = "day"'
              '}')
        {
        'body': [
        {
          'discriminant': {
            'type': 'CallExpression',
            'arguments': [

            ],
            'callee': {
              'computed': False,
              'object': {
                'type': 'NewExpression',
                'arguments': [

                ],
                'callee': {
                  'name': 'Date',
                  'type': 'Identifier'
                }
              },
              'property': {
                'name': 'getDay',
                'type': 'Identifier'
              },
              'type': 'MemberExpression'
            }
          },
          'type': 'SwitchStatement',
          'cases': [
            {
              'test': {
                'value': 0.0,
                'type': 'Literal',
                'raw': None
              },
              'consequent': [
                {
                  'type': 'ExpressionStatement',
                  'expression': {
                    'left': {
                      'name': 'day',
                      'type': 'Identifier'
                    },
                    'operator': '=',
                    'type': 'AssignmentExpression',
                    'right': {
                      'value': 'Sunday',
                      'type': 'Literal',
                      'raw': None
                    }
                  }
                },
                {
                  'label': None,
                  'type': 'BreakStatement'
                }
              ],
              'type': 'SwitchCase'
            },
            {
              'test': {
                'value': 1.0,
                'type': 'Literal',
                'raw': None
              },
              'consequent': [
                {
                  'type': 'ExpressionStatement',
                  'expression': {
                    'left': {
                      'name': 'day',
                      'type': 'Identifier'
                    },
                    'operator': '=',
                    'type': 'AssignmentExpression',
                    'right': {
                      'value': 'Saturday',
                      'type': 'Literal',
                      'raw': None
                    }
                  }
                },
                {
                  'label': None,
                  'type': 'BreakStatement'
                }
              ],
              'type': 'SwitchCase'
            },
            {
              'test': None,
              'consequent': [
                {
                  'type': 'ExpressionStatement',
                  'expression': {
                    'left': {
                      'name': 'day',
                      'type': 'Identifier'
                    },
                    'operator': '=',
                    'type': 'AssignmentExpression',
                    'right': {
                      'value': 'day',
                      'type': 'Literal',
                      'raw': None
                    }
                  }
                }
              ],
              'type': 'SwitchCase'
            }
          ]
        },
        {
          'type': 'EmptyStatement'
        }
      ],
      'type': 'Program'
    }


# Example 5

    >>> from farsiscript import FsParser
    >>> p = FsParser()
    >>> p.parse('motaghayer x = 15 * 5;'
              'eshkalzodaee;'
              'document.getElementById("demo").innerHTML = x;')
    {
    'type': 'Program',
    'body': [
        {
          'type': 'VariableDeclaration',
          'declarations': [
            {
              'type': 'VariableDeclarator',
              'init': {
                'type': 'BinaryExpression',
                'right': {
                  'type': 'Literal',
                  'value': 5.0,
                  'raw': None
                },
                'left': {
                  'type': 'Literal',
                  'value': 15.0,
                  'raw': None
                },
                'operator': '*'
              },
              'id': {
                'name': 'x',
                'type': 'Identifier'
              }
            }
          ],
          'kind': 'motaghayer'
        },
        {
          'type': 'DebuggerStatement'
        },
        {
          'type': 'ExpressionStatement',
          'expression': {
            'type': 'AssignmentExpression',
            'right': {
              'name': 'x',
              'type': 'Identifier'
            },
            'left': {
              'object': {
                'type': 'CallExpression',
                'callee': {
                  'object': {
                    'name': 'document',
                    'type': 'Identifier'
                  },
                  'type': 'MemberExpression',
                  'property': {
                    'name': 'getElementById',
                    'type': 'Identifier'
                  },
                  'computed': False
                },
                'arguments': [
                  {
                    'type': 'Literal',
                    'value': 'demo',
                    'raw': None
                  }
                ]
              },
              'type': 'MemberExpression',
              'property': {
                'name': 'innerHTML',
                'type': 'Identifier'
              },
              'computed': False
            },
            'operator': '='
          }
        },
        {
          'type': 'EmptyStatement'
        }
      ]
    }



License
----

MIT