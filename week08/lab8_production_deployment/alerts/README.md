# Lab 6 Alert Artifact

The alert JSON is kept local for now and is not declared as a Lab 8 bundle resource. Its query is hardcoded to `lab5.gold.agg_daily_sales`, so it cannot safely serve both the Lab 8 `dev` and `prod` targets without an explicit environment-parameterization strategy.
