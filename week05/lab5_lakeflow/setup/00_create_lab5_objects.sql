{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": 0,
   "metadata": {
    "application/vnd.databricks.v1+cell": {
     "cellMetadata": {
      "byteLimit": 104857600,
      "rowLimit": 1000
     },
     "inputWidgets": {},
     "nuid": "4af0d515-68e3-4eef-8bbc-408ac8debe36",
     "showTitle": false,
     "tableResultSettingsMap": {},
     "title": ""
    }
   },
   "outputs": [],
   "source": [
    "CREATE CATALOG IF NOT EXISTS lab5;\n",
    "CREATE SCHEMA IF NOT EXISTS lab5.bronze;\n",
    "CREATE SCHEMA IF NOT EXISTS lab5.silver;\n",
    "CREATE VOLUME IF NOT EXISTS lab5.bronze.checkpoints;\n",
    "CREATE VOLUME IF NOT EXISTS lab5.bronze.customer_landing;"
   ]
  }
 ],
 "metadata": {
  "application/vnd.databricks.v1+notebook": {
   "computePreferences": null,
   "dashboards": [],
   "environmentMetadata": null,
   "inputWidgetPreferences": null,
   "language": "sql",
   "notebookMetadata": {
    "pythonIndentUnit": 4,
    "sqlQueryOptions": {
     "applyAutoLimit": true,
     "catalog": "workspace",
     "schema": "default"
    }
   },
   "notebookName": "00_create_lab5_objects.dbquery.ipynb",
   "widgets": {}
  },
  "language_info": {
   "name": "sql"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 0
}
