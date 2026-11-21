# Full context versus focused harness

One endpoint: exact deliverable quantity.

| Approach | Correct | Accuracy | Median seconds | Input tokens | Output tokens |
|---|---:|---:|---:|---:|---:|
| baseline | 45/50 | 90.0% | 2.42 | 1,447,038 | 7,887 |
| harness | 46/50 | 92.0% | 3.23 | 89,044 | 6,752 |

Harness improvement: **+2.0 percentage points**. Paired wins/losses/ties: 3/2/45. Paired-bootstrap 95% interval: [-6.0, +10.0] pp. Exact paired p=1.0000.

10,000 paired-bootstrap draws. One model and one observation per approach/question; synthetic cases from one generator. A degenerate bootstrap interval does not establish equivalence.

| Question | Expected | Full context | Harness |
|---|---:|---:|---:|
| evaluation-1000 | 27 | 27 ✓ | 27 ✓ |
| evaluation-1001 | 0 | 0 ✓ | 0 ✓ |
| evaluation-1002 | 0 | 0 ✓ | 0 ✓ |
| evaluation-1003 | 40 | 40 ✓ | 40 ✓ |
| evaluation-1004 | 14 | 14 ✓ | 14 ✓ |
| evaluation-1005 | 21 | 21 ✓ | 21 ✓ |
| evaluation-1006 | 8 | 8 ✓ | 8 ✓ |
| evaluation-1007 | 0 | 0 ✓ | 0 ✓ |
| evaluation-1008 | 19 | 19 ✓ | 19 ✓ |
| evaluation-1009 | 40 | 40 ✓ | 40 ✓ |
| evaluation-1010 | 5 | 5 ✓ | 5 ✓ |
| evaluation-1011 | 0 | 0 ✓ | 0 ✓ |
| evaluation-1012 | 25 | 25 ✓ | 25 ✓ |
| evaluation-1013 | 16 | 16 ✓ | 16 ✓ |
| evaluation-1014 | 0 | 0 ✓ | 0 ✓ |
| evaluation-1015 | 0 | 0 ✓ | 0 ✓ |
| evaluation-1016 | 0 | 0 ✓ | 20 ✗ |
| evaluation-1017 | 39 | 39 ✓ | 39 ✓ |
| evaluation-1018 | 30 | 30 ✓ | 30 ✓ |
| evaluation-1019 | 0 | 0 ✓ | 0 ✓ |
| evaluation-1020 | 34 | 34 ✓ | 38 ✗ |
| evaluation-1021 | 22 | 22 ✓ | 22 ✓ |
| evaluation-1022 | 10 | 10 ✓ | 10 ✓ |
| evaluation-1023 | 17 | 17 ✓ | 17 ✓ |
| evaluation-1024 | 5 | 5 ✓ | 5 ✓ |
| evaluation-1025 | 19 | 19 ✓ | 19 ✓ |
| evaluation-1026 | 11 | 11 ✓ | 11 ✓ |
| evaluation-1027 | 40 | 40 ✓ | 40 ✓ |
| evaluation-1028 | 0 | 0 ✓ | 0 ✓ |
| evaluation-1029 | 29 | 33 ✗ | 33 ✗ |
| evaluation-1030 | 24 | 24 ✓ | 24 ✓ |
| evaluation-1031 | 0 | 0 ✓ | 0 ✓ |
| evaluation-1032 | 31 | 31 ✓ | 31 ✓ |
| evaluation-1033 | 54 | 55 ✗ | 54 ✓ |
| evaluation-1034 | 13 | 13 ✓ | 13 ✓ |
| evaluation-1035 | 0 | 0 ✓ | 0 ✓ |
| evaluation-1036 | 22 | 22 ✓ | 22 ✓ |
| evaluation-1037 | 0 | 0 ✓ | 0 ✓ |
| evaluation-1038 | 22 | 22 ✓ | 22 ✓ |
| evaluation-1039 | 45 | 45 ✓ | 45 ✓ |
| evaluation-1040 | 0 | 0 ✓ | 0 ✓ |
| evaluation-1041 | 34 | 39 ✗ | 34 ✓ |
| evaluation-1042 | 21 | 21 ✓ | 21 ✓ |
| evaluation-1043 | 16 | 16 ✓ | 16 ✓ |
| evaluation-1044 | 25 | 25 ✓ | 25 ✓ |
| evaluation-1045 | 32 | 36 ✗ | 36 ✗ |
| evaluation-1046 | 0 | 0 ✓ | 0 ✓ |
| evaluation-1047 | 0 | 0 ✓ | 0 ✓ |
| evaluation-1048 | 16 | 16 ✓ | 16 ✓ |
| evaluation-1049 | 35 | 49 ✗ | 35 ✓ |
