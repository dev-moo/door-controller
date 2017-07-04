
<?php

include 'door_config.php';
include 'get_ip_addr.php';
include 'get_mac_addr.php';
include 'mysql_query.php';
include 'udpcomms.php';


//Function to open door
function open_door($username){
	
	Global $doorsocket;
	
	$doorsocket->transmit_data(json_encode(array('OPERATION' => "SET", "TYPE" => "ACTIVATE", 'USER' => $username)));
	$tmp=$doorsocket->receive_data();
}

//Function to get status
function get_door_status(){
	
	Global $doorsocket;
	
	$doorsocket->transmit_data(json_encode(array('OPERATION' => 'GET')));
	$status = json_decode($doorsocket->receive_data())->STATUS;
	if(is_null($status)){return NULL;}
	
	return (bool)$status;
}

function log_activity($activity){
	
	/*Log activities to MySQL*/
	
	Global $door_closed, $user_name, $client_mac, $client_ip, $mysql_servername, $mysql_username, $mysql_password, $mysql_dbname;
	
	$current_status = 'Open';
	if($door_closed){$current_status = 'Closed';}
	
	$insert_cmd = sprintf("INSERT INTO http_users.logs (name, mac, ip, current_status, operation, time) VALUES ('%s', '%s', '%s', '%s', '%s', now())", $user_name, $client_mac, $client_ip, $current_status, $activity);
	query_mysql($mysql_servername, $mysql_username, $mysql_password, $mysql_dbname, $insert_cmd);	
		
}

function send_email($username){
    /*Send notification email*/
    
    Global $email_addr;
    
    $msg = sprintf("Door activated by %s at %s", $username, date('Y-m-d H:i:s'));
    mail($email_addr, "Door Activated - " . $username, $msg);         
}

//Object to communicate over UDP
$doorsocket = new UDPComms($door_server, $door_port);

//Get details of client device
$client_ip = get_ip_addr();
$client_mac = get_mac_address($client_ip);

//Lookup user in mysql DB
$sql_qry = "SELECT name, disabled, notify FROM http_users.users where mac_address = \"" . $client_mac . "\"";
$user = query_mysql($mysql_servername, $mysql_username, $mysql_password, $mysql_dbname, $sql_qry);

#Declare variables w/ default values
$user_name = "Stranger";
$disabled = True;
$notify = False;
$door_closed = True;
$online = True;  

//Process user 
if(is_null($user)){
	//Unknown user
	$user_name = "Stranger";
	$notify = True;

} else {
	//Known user
	$user_name = $user["name"];
	if($user["disabled"] != 1){$disabled = False;}
	if($user["notify"] == 1){$notify = True;}
}


//Process requests

if($_REQUEST['OP'] == 'activate' && !$disabled){
	
	//Open/close door for user user that is enabled when requested
	open_door($user_name);
	
	$door_closed = get_door_status();
	
	if(is_null($door_closed)){$online = False;}
    
	//Log entry to database
	log_activity('Activate');    

	if($notify){
		//Send email notification
        send_email($user_name);
	}

} elseif ($_REQUEST['OP'] == 'activate' && strlen($_REQUEST['PW']) > 0){
	
	/*Open door for unknown user with password*/
	
	//Get password hash from password input
	$password = hash("sha256", $_REQUEST['PW']); 
	
	//Retrieve password from db
	$sql_qry = "SELECT password FROM http_users.users where name = \"" .$user_name . "\"";
	$stored_pw = query_mysql($mysql_servername, $mysql_username, $mysql_password, $mysql_dbname, $sql_qry);
	
	if(!is_null($stored_pw)){
		$stored_pw = $stored_pw["password"];
		
		//Check if passwords match
		if($password == $stored_pw){
			open_door($user_name);
			
			//NOTIFY SUCCESS
			log_activity('PW Activate Success');
            send_email($user_name);
			
		} else {
			//NOTIFY FAILURE
			log_activity('PW Activate Failure');
            //send_email($user_name);
		}
	}
	
	
} else { 

	//Status update
	$door_closed = get_door_status();

	//Check response is valid
	if(is_null($door_closed)){$online = False;}
	
	log_activity('Status Request');
}

//Output
echo json_encode(array('name' => $user_name, 'disabled' => $disabled, 'notify' => $notify, 'IP' => $client_ip, 'MAC' => $client_mac, 'online' => $online, 'door_closed' => $door_closed))

?>