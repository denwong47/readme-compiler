import unittest

import readme_compiler.format as format

class TestFormat(unittest.TestCase):
    
    def test_link_anchor(self):
        _tests = {
            "#### Test"                                         :   "#test",
            "# Branch: `DF-114-back-end-centralisation`"        :   "#branch-df-114-back-end-centralisation",
            "#  !\"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~":\
                                                                    "#0123456789abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyz",
            "#          -----"                                  :   "#", # This is probably not valid but that's how VSCode deal with it
            "# -A- - - - - - -"                                 :   "#a",
            "# -A- - - - - - -A- - "                            :   "#a-------------a",
        }
        
        tuple(map(
            lambda input: self.assertEqual(
                format.link_anchor(input),
                _tests[input],
            ),
            _tests,
        ))
        


if __name__=="__main__":
    unittest.main()