from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import ASYNCHRONOUS

from core.config import config


org = config.influx.org

print("Initializing influxdb client...")
client = InfluxDBClient(url=config.influx.url, token=config.influx.token, org=org)

bucket = "logs"

print("Initializing influxdb write api...")
write_api = client.write_api(write_options=ASYNCHRONOUS)

query_api = client.query_api()


def ilog(point: Point):
    if not config.influx.enable:
        return
    write_api.write(bucket=bucket, record=point)
