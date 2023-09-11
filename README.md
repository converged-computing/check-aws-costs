# AWS Cost Check

We need an automated means to check for cases that can lead to bad times with billing.

- Instances left on (and forgotten)
- Storage / Volumes attached to off-instances

Likely the way we monitor these will depend on the project. For example, a project that regularly runs long analyses would not want an alert for an instance up a day. Much of the analysis would come down to looking for either patterns or outliers. Since outliers require some kind of model and historical data, I'm going to (at first) go for more of a logical approach - identifying the patterns to be concerned about, and then assessing:

- total lump sums of things
- big rates of change between timepoints
- going above some threshold

I want to start by reading about some of these patterns and taking notes, and asking:

1. What is the pattern?
2. What are we looking for?

A third idea I'm also thinking is that it might be easy enough to just plot everything we have, over time, and send an email (or similar) to a human to look at it. I might just start with this because it's simple and easy.

## Usage

```bash
pip install -r requirements.txt
python check-aws-costs.py
```
```console
Querying for daily cost by service for us-east-1
Querying for daily cost by service for us-east-2
Querying for daily cost by service for us-west-1
Querying for daily cost by service for us-west-2
Saving raw results to cache/spending-2023-09-11.json
Adding us-east-1 to the data frame...
Adding us-east-2 to the data frame...
Adding us-west-1 to the data frame...
Adding us-west-2 to the data frame...
Saving formatted results to cache/spending-2023-09-11.csv
```

## References

 - [AWS Cost-Saving Gotchas](https://medium.com/@matt_weingarten/aws-cost-saving-gotchas-f0f883c34c69)
