# The Question
Question: How does the rotten tomato's score affect a movies profitability? Audience score?
Specific question: Is there a linear association between a films rotten tomatos score and the profitability of the film? Audience score?

# What Is The Data?
The data was collected by the Lock5, a family of statisticians, for the use in a textbook created by them. They've collected 140 datasets for this textbook. They collected the data from the-numbers.org and the Rotten Tomatos official site. The data can be found here: https://www.lock5stat.com/datapage4e.html
After an initial analysis of the variables, I found that in the most recent form of the dataset, over half of the rows were dropped due to missing budget. Because of this, I decided to append data from earlier versions of the dataset. In this instance, earlier versions contained data of films from a different time period, such as 2007-2011 and 2012-2018. Because the data is still unique, it triples the usable data and likely will not skew results. This results in 3109 rows of data to run analysis on.

# Variables Used
### RottenTomatoes
- Non-Missing : 2983
- Missing : 126
- Mean : 58.35
- Median : 62
- SD : 27.42
- Range : 0 - 100
![Histogram](./figures/histogram_RottenTomatoes.png)
### AudienceScore
- Non-Missing : 3026
- Missing : 83
- Mean : 65.94
- Median : 67
- SD : 18.85
- Range : 0 - 100
![Histogram](./figures/histogram_AudienceScore.png)
### WorldwideBO (in millions)
- Non-Missing : 2897
- Missing : 212
- Mean : 145.56
- Median : 54.04
- SD : 244.91
- Range : 0.1 - 2781.5
![Histogram](./figures/histogram_WorldwideBO.png)
The worldwide box office is heavily skewed right so certain tests will not work as well.
### Budget (in millions)
- Non-Missing : 2332
- Missing : 777
- Impossible : 1
- Mean : 55.59
- Median : 33
- SD : 59.21
- Range : 0.0 - 400
![Histogram](./figures/histogram_Budget.png)

When cleaning the data, all rows with missing or impossible values were dropped, which totaled to 796 rows being dropped. Additionally, duplicated rows from appending the datasets are dropped. This leaves me with 2098 rows to run analysis on.

### How To Determine Profitability
In the dataset, there is a profit column, but this column is simply determining if the film made back its stated budget. When it comes to the film industry, conventional wisdom states that a film must make back 2.5 times its budget to break even. This is due to theater distribution costs, marketing costs, etc. So to determine if a film is profitable, I will be checking its WorldwideBO against 2.5* the budget. The calculation will provide a number that is either negative or positive (or 0 if it truly broke even). Negative means the film lost that money, while postiive means it profited that money. To account for outliers, a binary variable will also be set on if the film is profitable. This is what will be used in the hypothesis test.

# Hypothesis
Because WorldwideBO is heavily skewed right, a linear-association will not work. To account for this, profitability will be a binary outcome and will be compared against well reviewed and poorly reviewed scores.

**Definitions**
Profitable : Is WorldwideBO >= 2.5*Budget?
Fresh (critics) : Is RottenTomatoes >= 60?
Fresh (audience) : Is AudienceScore >= 60?
p_Fresh = percentage of fresh movies that are profitable
p_Rotten = percentage of rotten movies that are profitable

### Test 1
Two-Proportion z-test
H_0 : The proportion of profitable films is the same for critic certified-fresh and critic rotten films.
H_0 : p_Fresh - p_Rotten = 0
H_1 : The proportion of profitable films differs for critic certified-fresh and critic rotten films.
H_1 : p_Fresh - p_Rotten != 0

### Test 2
Two-Proportion z-test
H_0 : The proportion of profitable films is the same for audience certified-fresh and audience rotten films.
H_0 : p_Fresh - p_Rotten = 0
H_1 : The proportion of profitable films differs for audience certified-fresh and audience rotten films.
H_1 : p_Fresh - p_Rotten != 0

## More Info
The tests are two-sided since there could be a difference in either direction.

I will use a significance level of a=0.025 because I am running 2 tests so this keeps the false positive rate at only 5%. If I kept it at a=0.05 then the FP rate would be 10%. 

The minimum result that matters is a significant test with 10 percentage points. |p_Fresh − p_Rotten| >= 0.10 and p < 0.025

# Initial Results
## Critic Score
```
p_Fresh = 0.5882
p_Rotten = 0.43
p_Fresh - p_Rotten = 0.1582
z = 7.2369
p < 0.000001
CI [11.59, 20.05]
```
This shows that there is statistical significance in the profitability of a film based on its RT Critic score. Reject H_0

## Audience Score
```
p_Fresh = 0.5746
p_Rotten = 0.4024
p_Fresh - p_Rotten = 0.1723
z = 7.7397
p < 0.000001
CI [12.93, 21.52]
```
This shows that there is statistical significance in the profitability of a film based on its RT Audience score. Reject H_0

# Assumptions / Concerns
Each row is a seperate film, which does not rely on others. When checking this I found some duplicate films from overlap of the year 2013, so I added code to clean that. 
With 2100 films, I set the statistical significance to 10 percentage points because with the way the test is setup, even a few films could be detectable, but not useful.
This sample contains bias in the sense that only films that broke $100k at the box office were included, so it doesn't include total flops, direct-to-streaming releases, or films that didn't report a boxoffice or budget.
Because I did multiple comparissons I used a Bonferroni corrected a value to keep the false positive rate about 5%.
Some possible confounding variables could be: franchise film, year, market conditions, marketing budget, studio, stars, filmmakers, etc.
One thing to note about the data is that budget is an estimate based on reports from the industry that are published, studios don't typically publish the exact budget.
I would also like to take a look at how the audience vs critic scores relate, especially on highly successful films.