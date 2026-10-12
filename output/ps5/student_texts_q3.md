# Student's own texts for Homework 5, Question 3 (Problem Set 5)

These texts are written by the student and go into the submission as the student's own work. The AI may correct spelling and grammar only, when asked.

## Task 6: Hypotheses

We want to test whether average inflation-adjusted childcare worker wages were the same in 2019 and 2022. So we create H0: mu 2022 = mu 2019, which means mu 2022 - mu 2019 = 0. That means our H alternative: mu 2022 – mu 2019 unequal to 0. H0 means no real wage change. Therefore, we want to run a two-sided hypothesis test.

## Task 6: Choice of test

I chose a two-sided test done at the metro area level. We want to match the metro areas to one another for this test, so that the same areas are compared for 2019 and 2022. That allows us to better test H0 and see if the inflation-adjusted wages were the same. The data is measured at the metro level. If we were to choose the county level, we would have multiple counties with the same wage level. We want to stay as close to the structure behind the original data as possible.

## Task 6: Test result and conclusion

The p-value of the test is 0.000011, which is much smaller than the alpha of 5%. Therefore, we reject H0. The results show clear evidence that the childcare workers’ wages changed over this period. The averages increased from $27,207.57 in 2019 to $27,704.73 in 2022, meaning the change is an increase. That supports the providers' claim, but the increased wages do not have to be the reason for increased costs following the Covid-19 pandemic. Further, the increase was relatively small (+1.83%, i.e. +$497.16 per year from 2019 to 2022).

## Task 7: Method

I use a bivariate OLS regression at the county level with the standard errors clustered by metro area. Female college share is measured at the county level, whereas the childcare workers’ wages are measured at the metro level. Counties within the same metro have the same wage. Claude suggested clustering the SE at the metro-area level to account for this, which I agree with. Therefore, Y = a + bX + e, with Y = childcare worker wage and X = female college share.

## Task 7: Hypothesis test

For the hypothesis test, we want to test whether there is no relationship between the two, so H0: b=0 and HA: b unequal 0.

## Task 7: Decision and interpretation

We have p < 0.0001, meaning that with alpha = 5% we can reject H0. There is strong evidence that the coefficient on female college share is different from 0. The coefficient is 16,499.99, and female college share is measured from 0 to 1. Therefore, a 10-percentage-point increase in the share of women age 25 and older with a bachelor’s degree or higher is associated with $1,650 higher annual childcare-worker wages, on average. This does not mean that a higher female college share causes higher wages. More educated areas tend to be richer and more expensive overall, which raises all wages, including childcare wages.
