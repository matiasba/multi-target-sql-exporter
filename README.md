# Multi-target SQL Exporter

There is a bunch of SQL Prometheus exporters out there like but not one follows the multi-target pattern correctly and depend on files with static targets and fixed scrape intervals. Those exporters didn't  cover my use case so I slap together this bad boy. Hopefully someone who actually knows how to code will rewrite it in go and make it nice like the [Blackbox exporter](https://github.com/prometheus/blackbox_exporter). 

**Important: This only works with MySQL for now**\
I will try to make it PostgreSQL compatible at some point (maybe)

## How it works

The exporter publish `/scrape` endpoint where it waits for a request with the following parameters:\
**host** hostname or ip of target database\
**port** *optional parameter* will default to 3306\
**database** database on which the query package will be executed\
**package**  name of the package of queries that will be executed on the target from `queries.yaml`\
**auth** name of the auth credential to use from `auth.yaml`

Example of simple *Prometheus* static config:

	scrape_configs:
	  - job_name: multi-sql-exporter-static
	    scheme: http
	    params:
	      auth: generic-monitoring
	      package: custom-monitoring
	    static_configs:
	      - targets: 
	        - 'my-database.local'
	    relabel_configs:
	      - source_labels: [__address__]
	        target_label: __param_target
	      - target_label: __address__
	        replacement: localhost:9866

Example of `auth.yaml` config:\
*Question:* Why are the auth credentials store in a file inside the exporter?\
*Answer:* Because the Prometheus config doesn't provide a way to provide the credentials in a secure way, if passed as a parameter It will always be shown in the Prometheus targets list as a discovered label. You can have this file provisioned during deployment based on your current credentials and redeploy the app when you need to roll credentials.

	auths:  
	  generic-monitoring:  
	    user: "dummy"  
	    password: "pass12345"  
	  generic-monitoring-external:  
	    user: "dummy"  
	    password: "pass12345"  

Example of `queries.yaml` config:\
You can have multiple queries defined on the same package, they will be executed in series and all the metrics generated will return together\
You can have multiple metrics defined in a single query, each value column will be a metric and each label must be a column in the result set.

	packages:
	  custom-monitoring:
	    - name: "db_size"
	      query: "SELECT table_schema AS 'database', ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'size_mb' FROM information_schema.TABLES GROUP BY table_schema ORDER BY 2 desc"
	      labels:
	        - "database"
	      values:
	        - column: "size_mb"
	          type: "gauge"
	          help: "Database Size in MB"
Will return:

	# HELP db_size_size_mb Database Size in MB
	# TYPE db_size_size_mb gauge
	db_size_size_mb{database="sys"} 0.02
	db_size_size_mb{database="admin_tools"} 0.02
	db_size_size_mb{database="performance_schema"} 0.0
	db_size_size_mb{database="information_schema"} 0.0

### More complex usage
Example data:

	"ID","amount","seller","country"
	"1","1000","Pedro","ARG"
	"2","200","Carlos","BR"
	"3","600","Pedro","BR"
	"4","200","Pedro","ARG"
	"5","300","Carlos","BR"

Will extract a multi label metric

	packages:
	  custom-monitoring:
	    - name: "sales"
	      query: "SELECT count(1) as count, sum(amount) as amount, seller, country  FROM sales group by seller,country"
	      labels:
	        - "seller"
	        - "country"
	      values:
	        - column: "count"
	          type: "gauge"
	          help: "amount of sales"
	        - column: "amount"
	          type: "gauge"
	          help: "sum of sales"
	          
Will return:

	# HELP sales_count amount of sales
	# TYPE sales_count gauge
	sales_count{seller="Carlos",country="BR"} 2.0
	sales_count{seller="Pedro",country="ARG"} 2.0
	sales_count{seller="Pedro",country="BR"} 1.0
	# HELP sales_count amount of sales
	# TYPE sales_count gauge
	sales_amount{seller="Carlos",country="BR"} 500.0
	sales_amount{seller="Pedro",country="ARG"} 1200.0
	sales_amount{seller="Pedro",country="BR"} 600.0