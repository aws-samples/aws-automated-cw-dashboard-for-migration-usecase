import boto3
import json
import sys


REGION=<region>

cw_client = boto3.client('cloudwatch',region_name=REGION)
mgn_client = boto3.client('mgn',region_name=REGION)
ec2_client = boto3.client('ec2', region_name=REGION)


def lambda_handler(event, context):
	sourceServers = get_all_source_servers()
	push_machine_test_cutover_metrics(sourceServers)
	push_replication_state_metric(sourceServers)
	print ("Metrics created/updated on CloudWatch")
	put_dashboard_data(sourceServers)
	print ("CloudWatch Dashboard created/updated with 5 widgets")

def get_all_source_servers():
	'''Get all source servers from MGN console'''
	try:
		sourceServers = mgn_client.describe_source_servers(filters={'isArchived': False})		
	except:
		sys.exit("MGN Service is not initialized in this region")
	else:
		if sourceServers['items'] == []:
			sys.exit("No source Servers configured")
		return sourceServers['items']
	

def push_machine_test_cutover_metrics(sourceServers):
	'''Push Test machines data to cloudwatch'''
	tested_machines = []
	cutover_machines = []
	for sourceServer in sourceServers:
		state = sourceServer['lifeCycle']['state']
		if sourceServer['lifeCycle']['lastTest']['initiated']:
			if state == 'TESTING':
				if 'launchedInstance' in sourceServer:
					if sourceServer['launchedInstance']['jobID'] == sourceServer['lifeCycle']['lastTest']['initiated']['jobID']:
						if 'ec2InstanceID' in sourceServer['launchedInstance']:
							ec2InstanceID = sourceServer['launchedInstance']['ec2InstanceID']
							response = ec2_client.describe_instance_status(InstanceIds=[ec2InstanceID])
							instance_status_check = response['InstanceStatuses'][0]['InstanceStatus']['Status']
							if instance_status_check == 'ok':
								tested_machines.append(sourceServer['sourceServerID'])
			elif state == 'READY_FOR_CUTOVER':
				tested_machines.append(sourceServer['sourceServerID'])
				
			elif state == 'CUTTING_OVER':
				if 'launchedInstance' in sourceServer:
					if sourceServer['launchedInstance']['jobID'] == sourceServer['lifeCycle']['lastCutover']['initiated']['jobID']:
						if 'ec2InstanceID' in sourceServer['launchedInstance']:
							ec2InstanceID = sourceServer['launchedInstance']['ec2InstanceID']
							response = ec2_client.describe_instance_status(InstanceIds=[ec2InstanceID])
							instance_status_check = response['InstanceStatuses'][0]['InstanceStatus']['Status']
							if instance_status_check != 'ok':
								tested_machines.append(sourceServer['sourceServerID'])
						else:
							tested_machines.append(sourceServer['sourceServerID'])
				else:
							tested_machines.append(sourceServer['sourceServerID'])

		if sourceServer['lifeCycle']['lastCutover']['initiated']:
			if state == 'CUTTING_OVER':
				if 'launchedInstance' in sourceServer:
					if sourceServer['launchedInstance']['jobID'] == sourceServer['lifeCycle']['lastCutover']['initiated']['jobID']:
						if 'ec2InstanceID' in sourceServer['launchedInstance']:
							ec2InstanceID = sourceServer['launchedInstance']['ec2InstanceID']
							response = ec2_client.describe_instance_status(InstanceIds=[ec2InstanceID])
							instance_status_check = response['InstanceStatuses'][0]['InstanceStatus']['Status']
							if instance_status_check == 'ok':
								cutover_machines.append(sourceServer['sourceServerID'])
			elif state == 'CUTOVER':
				cutover_machines.append(sourceServer['sourceServerID'])
				
	try:
		cw_client.put_metric_data(
				Namespace='AWS MGN',
				MetricData=[
					{
						'MetricName': 'TotalMachinesTested',
						'Dimensions': [],
						'Unit': 'Count',
						'Value': len(tested_machines)
					}
				]
			)
			
		cw_client.put_metric_data(
				Namespace='AWS MGN',
				MetricData=[
					{
						'MetricName': 'TotalMachinesCutover',
						'Unit': 'Count',
						'Value': len(cutover_machines)
					}
				]
			)
	except Exception as e:
		print (e)


def push_replication_state_metric(sourceServers):
	'''Push Replication data to cloudwatch'''
	fully_replicated_machines = []
	machines_syncing = []
	for sourceServer in sourceServers:
		replication_state = sourceServer['dataReplicationInfo']['dataReplicationState']
		if replication_state == 'DISCONNECTED':
			continue
		elif replication_state == 'CONTINUOUS':
			fully_replicated_machines.append(sourceServer['sourceServerID'])
		else:
			machines_syncing.append(sourceServer['sourceServerID'])
	cw_client.put_metric_data(
			Namespace='AWS MGN',
			MetricData=[
				{
					'MetricName': 'MachinesFullySynced',
					'Dimensions': [],
					'Unit': 'Count',
					'Value': len(fully_replicated_machines)
				}
			]
		)
	cw_client.put_metric_data(
			Namespace='AWS MGN',
			MetricData=[
				{
					'MetricName': 'MachinesSyncing',
					'Dimensions': [],
					'Unit': 'Count',
					'Value': len(machines_syncing)
				}
			]
		)

def put_dashboard_data(sourceServers):
	'''Create CloudWatch Dashboard'''
	durationSinceLastTest = [[ "AWS/MGN", "DurationSinceLastTest", "SourceServerID"]]
	backlog = [[ "AWS/MGN", "Backlog", "SourceServerID"]]
	elapsedReplicationDuration = [[ "AWS/MGN", "ElapsedReplicationDuration", "SourceServerID"]]
	lagDuration = [[ "AWS/MGN", "LagDuration", "SourceServerID"]]
	for sourceServer in sourceServers:
		if sourceServer['lifeCycle']['state'] == 'DISCONNECTED':
			continue
		if len(durationSinceLastTest[0]) != 3:
			durationSinceLastTest.append(["...",sourceServer['sourceServerID']])
			backlog.append(["...",sourceServer['sourceServerID']])
			elapsedReplicationDuration.append(["...",sourceServer['sourceServerID']])
			lagDuration.append(["...",sourceServer['sourceServerID']])
		else:
			durationSinceLastTest[0].append(sourceServer['sourceServerID'])
			backlog[0].append(sourceServer['sourceServerID'])
			elapsedReplicationDuration[0].append(sourceServer['sourceServerID'])
			lagDuration[0].append(sourceServer['sourceServerID'])
	try:
		response = cw_client.get_dashboard(DashboardName='MGN-Dashboard')
		dashboard_json = json.loads(response['DashboardBody'])
		
	except:
		dashboard_json = {
		"widgets": [
			{
				"height": 6,
				"width": 6,
				"y": 0,
				"x": 12,
				"type": "metric",
				"properties": {
					"view": "timeSeries",
					"metrics": [[ "AWS/MGN", "DurationSinceLastTest", "SourceServerID"]],
					"region": REGION,
					"stacked": False
				}
			},
			{
				"height": 6,
				"width": 6,
				"y": 0,
				"x": 0,
				"type": "metric",
				"properties": {
					"view": "pie",
					"metrics": [
						[ "AWS/MGN", "ActiveSourceServerCount" ],
						[ ".", "TotalSourceServerCount" ]
					],
					"region": REGION,
					"stat": "Maximum",
                	"period": 60
				}
			},
			{
				"height": 6,
				"width": 6,
				"y": 0,
				"x": 18,
				"type": "metric",
				"properties": {
					"view": "pie",
					"metrics": [[ "AWS/MGN", "Backlog", "SourceServerID"]],
					"region": REGION
				}
			},
			{
				"height": 6,
				"width": 6,
				"y": 0,
				"x": 6,
				"type": "metric",
				"properties": {
					"view": "bar",
					"metrics": [[ "AWS/MGN", "ElapsedReplicationDuration", "SourceServerID"]],
					"region": REGION,
					"setPeriodToTimeRange": True
				}
			},
			{
				"height": 6,
				"width": 6,
				"y": 6,
				"x": 0,
				"type": "metric",
				"properties": {
					"view": "timeSeries",
					"metrics": [[ "AWS/MGN", "LagDuration", "SourceServerID"]],
					"stacked": False,
					"region": REGION
				}
			}
		]
	}
	finally:
		widgets = dashboard_json['widgets']
		for widget in widgets:
			if widget['properties']['metrics'][0][1] == "DurationSinceLastTest":
				widget['properties']['metrics'] = durationSinceLastTest
			elif widget['properties']['metrics'][0][1] == "Backlog":
				widget['properties']['metrics'] = backlog
			elif widget['properties']['metrics'][0][1] == "ElapsedReplicationDuration":
				widget['properties']['metrics'] = elapsedReplicationDuration
			elif widget['properties']['metrics'][0][1] == "LagDuration":
				widget['properties']['metrics'] = lagDuration
			elif widget['properties']['metrics'][0][1] == "MachinesSyncing" or widget['properties']['metrics'][0][1] == "MachinesFullySynced":
				widget['properties']['stat'] = "Maximum"
				widget['properties']['period'] = 1
			elif widget['properties']['metrics'][0][1] == "TotalMachinesCutover" or widget['properties']['metrics'][0][1] == "TotalMachinesTested":
				widget['properties']['stat'] = "Maximum"
				widget['properties']['period'] = 60
		dashboard_body = json.dumps(dashboard_json)
		cw_client.put_dashboard(
		DashboardName='MGN-Dashboard',
		DashboardBody= dashboard_body
	)

