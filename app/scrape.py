from flask import request, jsonify, Blueprint
from prometheus_client import generate_latest, CollectorRegistry, Gauge, Counter
from pymysql.err import OperationalError, ProgrammingError
from app import auth_config, queries_config, execute_query

scrape = Blueprint('scrape', __name__)


@scrape.route('/scrape', methods=['GET'])
def scrape_endpoint():
    target = request.args.get('target')
    port = request.args.get('port', 3306, type=int)
    database = request.args.get('database')
    package = request.args.get('package')
    auth = request.args.get('auth')

    if not all([target, database, package, auth]):
        return jsonify({"error": "host, database, package, and auth parameters are required"}), 400

    if package not in queries_config['packages']:
        return jsonify({"error": f"package '{package}' not found"}), 404

    if auth not in auth_config['auths']:
        return jsonify({"error": f"auth '{auth}' not found"}), 404

    db_config = {
        'host': target,
        'port': port,
        'user': auth_config['auths'][auth]['user'],
        'password': auth_config['auths'][auth]['password'],
        'database': database
    }

    registry = CollectorRegistry()
    try:
        for query in queries_config['packages'][package]:
            cursor_description, results = execute_query(db_config, query['query'])
            labels = query.get('labels', [])
            values = query.get('values', {})

            # Map column names to their indices
            column_names = [desc[0] for desc in cursor_description]
            value_indexes = []
            metrics = {}
            for value in values:
                value_indexes.append(column_names.index(value['column']))

                metrics_properties = [d for d in values if d['column'] == value['column']]

                if len(metrics_properties) > 1:
                    return jsonify({"error": f"There is multiple columns with the name: {value}"}), 400

                metric_type = metrics_properties[0]['type']
                metric_help = metrics_properties[0]['help']
                if metric_type == 'gauge':
                    metric = Gauge(f'{query["name"]}_{value['column']}', metric_help, registry=registry,
                                   labelnames=labels)
                elif metric_type == 'counter':
                    metric = Counter(f'{query["name"]}_{value['column']}', metric_help, registry=registry,
                                     labelnames=labels)
                else:
                    return jsonify({"error": f"Unsupported metric type: {metric_type}"}), 400
                metrics[value['column']] = metric

            for value in values:
                if value['column'] not in column_names:
                    return jsonify({"error": f"Value column '{value['column']}' not found in query result"}), 500

            for row in results:
                if len(row) != len(labels) + len(values):
                    return jsonify(
                        {"error": "Number of columns in query result does not match labels and values"}), 500

                # Extract labels
                label_values = {}
                for index, column in enumerate(row):
                    if index not in value_indexes:
                        label_values[column_names[index]] = column

                for index, column in enumerate(row):
                    if index in value_indexes:
                        # Extract values
                        value = column
                        value_name = column_names[index]
                        if labels:
                            metrics[value_name].labels(**label_values).set(value)
                        else:
                            metrics[value_name].set(value)

        return generate_latest(registry)

    except OperationalError as e:
        if e.args[0] in (1045, 1044):
            return jsonify({"error": "Authentication failed: Invalid username or password"}), 401
        elif e.args[0] == 2003:
            return jsonify({"error": "Cannot connect to database server"}), 503
        else:
            return jsonify({"error": "Database error", "details": str(e)}), 500
    except ProgrammingError as e:
        if e.args[0] == 1064:
            return jsonify({"error": "Error in your SQL syntax"}), 500
        else:
            return jsonify({"error": "Database error", "details": str(e)}), 500
    except ValueError as e:
        return jsonify({"error": "Label or value matching error", "details": str(e)}), 500
    except Exception as e:
        return jsonify({"error": "Unknown error", "details": str(e)}), 500
