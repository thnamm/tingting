#include <iostream>
#include <string>
#include <vector>

using namespace std;

class Solution {
public:
    char findTheDifference(string s, string t) {
        int sd = 0;
        for (size_t i = 0; i < t.size(); i++) {
            if (i < s.size()) sd += static_cast<int>(s[i]);
            sd -= static_cast<int>(t[i]);
        }
        return static_cast<char>(-sd);
    }
};


int main() {
    Solution sol;

    // Test cases: {s, t, expected}
    vector<pair<pair<string,string>, char>> tests = {
        {{"abcd", "abcde"}, 'e'},
        {{"", "y"}, 'y'},
        {{"a", "aa"}, 'a'},
        {{"ae", "aea"}, 'a'},
    };

    for (auto& [st, expected] : tests) {
        char result = sol.findTheDifference(st.first, st.second);
        cout << "s=\"" << st.first << "\", t=\"" << st.second << "\" -> "
             << result << " (expected: " << expected << ") "
             << (result == expected ? "PASS" : "FAIL") << "\n";
    }

    return 0;
}