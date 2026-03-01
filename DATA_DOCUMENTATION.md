# Crime Rate Data & Methodology Guide

This document explains the data generation approach, variables, and machine learning methodology used in the **Crime Rate Prediction System – India**.

---

## 1. Synthetic Data Generation

Since raw, granular NCRB (National Crime Records Bureau) structural data is often unavailable or fragmented, this system dynamically creates a structurally realistic synthetic dataset representing 29 Indian States and UTs over a 15-year period (2010–2024). 

The data is logically seeded with state-specific baselines (e.g. higher population and urbanisation in specific states like Maharashtra or UP) to simulate real-world regional disparity.

### Generated Features (Socioeconomic Indicators)

These are the independent variables ($X$) used to train the machine learning models. Each is logically correlated with the underlying simulated crime rate:

1. **`population`**  
   *What is it?* The total number of people living in the state for that specific year.  
   *Trend:* Grows steadily by ~1-2% annually.

2. **`unemployment_rate`**  
   *What is it?* The percentage of the active workforce currently unemployed.  
   *Trend:* Fluctuates based on simulated business cycles. *Strong positive correlation with crime rates.*

3. **`literacy_rate`**  
   *What is it?* Percentage of people (7 yrs+) who can read and write with understanding.  
   *Trend:* Gradually increases over the 15-year span. *Strong negative correlation with crime rates.*

4. **`urbanization_rate`**  
   *What is it?* Percentage of population living in urban areas vs rural areas.  
   *Trend:* Gradually increases over time as simulated populations migrate to cities. *Slight positive correlation with specific types of structural crime.*

5. **`police_strength_per_100k`**  
   *What is it?* Number of police personnel assigned per 100,000 citizens.  
   *Trend:* Adjusts over the years depending on population growth. *Strong negative correlation; regions with higher police presence trend downwards in crime over time.*

### The Target Variable (Y)

* **`crime_rate_per_100k`**  
  *What is it?* The number of reported crimes per 100,000 people in the given year.  
  *Calculation:* This is realistically synthesised from a weighted combination of the socioeconomic features above, plus a small amount of Gaussian noise (randomness/variance) to make the data organic and suitable for ML models to learn off.

### Time-Series Features (Lag Variables)

To turn standard socio-economic regression into powerful **Time-Series Forecasting**, the system automatically calculates lag features during the preprocessing phase:

* **`crime_rate_lag_1`**: The state's crime rate from the *previous year*.
* **`crime_rate_lag_2`**: The state's crime rate from *two years ago*.
* **`crime_rate_lag_3`**: The state's crime rate from *three years ago*.

> *Why do we use lag features?* The best predictor of a state's crime rate today is often its crime rate yesterday. Lag features give the Machine Learning algorithms a "memory" of recent historical trends.

---

## 2. Machine Learning Methodology

The system evaluates three robust regression models to capture both linear trends and complex, non-linear relationships within the structural data.

### The Models
1. **Linear Regression:** A baseline model that assumes a straight-line relationship between the socio-economic factors and crime rate. Good for overall baseline trends but struggles with nuanced variance.
2. **Random Forest Regressor:** An ensemble model that builds numerous decision trees. Highly resistant to overfitting and excellent at capturing sudden thresholds.
3. **XGBoost Regressor (Extreme Gradient Boosting):** A highly performant, state-of-the-art tree-boosting algorithm. Often the winner in structured tabular data like this, it sequentially builds trees that specifically correct the errors of previous trees.

### Traing & Test Split
We split the data chronologically holding out the final subset of years as our 'Test/Validation' data. 
* **Training Set:** 2010 to 2020.
* **Test Set:** 2021 to 2024.

### Model Evaluation Metrics
Once the models predict the testing set (2021-2024), we mathematically evaluate exactly how close they were to the actual (synthetic) truth using three metrics. The system then automatically saves the model with the highest **R² Score** as `model.pkl`.

* **$R^2$ Score (Coefficient of Determination)**  
  *What it means:* Evaluates the proportion of the variance in the dependent variable that is predictable from the features.  
  *Scale:* $0.0$ to $1.0$ (closer to 1.0 is better).

* **RMSE (Root Mean Squared Error)**  
  *What it means:* Measures the average magnitude of the error. Taking the square root ensures the metric is in the exact same unit as the target variable (Crime Rate per 100k).  
  *Scale:* Lower is better. Heavily penalises large, outlier predictions.

* **MAE (Mean Absolute Error)**  
  *What it means:* The absolute average difference between predicted and actual values.  
  *Scale:* Lower is better. Treats all errors equally.

---

## 3. The Forecasting Engine (Recursive Multi-Step)

When utilizing the **Generate Forecast** button on the dashboard for the future (e.g. 5 to 10 years), the system doesn't know the future "Unemployment Rate" or "Population". So how does it project into 2030?

We use a technique known as **Recursive Forecasting**:
1. First, the algorithm conservatively drifts the socioeconomic indicators forward by their recent historical averages (e.g. predicting a further 1% drop in illiteracy).
2. It then predicts year $Y+1$ using the actual past 3 years of lag data.
3. To predict year $Y+2$, it uses the **prediction** from year $Y+1$ as one of the new lag variables.
4. It recurses this process continuously to project 5 to 10 years into the future. 

### Risk Level Categorisation

The projected continuous float values for Crime Rate are binned into categorical human-readable bands shown on tables and maps:
* **🟢 Low Risk:** $< 150$ incidents per 100k
* **🟡 Medium Risk:** $150 - 300$ incidents per 100k
* **🔴 High Risk:** $> 300$ incidents per 100k
