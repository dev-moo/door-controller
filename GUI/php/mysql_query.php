
<?php


function query_mysql($servername, $username, $password, $dbname, $sql_query){

	// Create connection
	$conn = new mysqli($servername, $username, $password, $dbname);

	// Check connection
	if ($conn->connect_error) {
		return NULL;
	    //die("Connection failed: " . $conn->connect_error);
	} 

	$result = $conn->query($sql_query);

	if ($result->num_rows > 0) {
		$r = $result->fetch_assoc();
		$conn->close();
		return $r;
    }

	return NULL;
}

?>