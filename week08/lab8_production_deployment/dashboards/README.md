# Lab 6 Dashboard Artifact

The dashboard JSON is kept local for now and is not declared as a Lab 8 bundle resource. Its dataset sources are hardcoded to `lab5.gold.agg_daily_sales` and `lab5.gold.agg_customer_summary`, so it cannot safely serve both the Lab 8 `dev` and `prod` targets without an explicit environment-parameterization strategy. The existing Lab 6 resource also uses a hardcoded warehouse ID.
