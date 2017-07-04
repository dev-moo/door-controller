
<?php

class UDPComms{
	
	private $sock;
	public $server;
	public $port;
	
	
	private function create_socket(){
	 
		if(!($s = socket_create(AF_INET, SOCK_DGRAM, 0)))
		{
			$errorcode = socket_last_error();
			$errormsg = socket_strerror($errorcode);
			 
			die("Couldn't create socket: [$errorcode] $errormsg \n");
			
			return false;
		}
		
		return $s;
	}
	
	public function __construct($s, $p) {
		$this->server = $s;
		$this->port = $p;
		$this->sock = $this->create_socket();
	}
	

	public function transmit_data($data){
		
		//Send the message to the server
		if( ! socket_sendto($this->sock, $data , strlen($data) , 0 , $this->server , $this->port))
		{
			$errorcode = socket_last_error();
			$errormsg = socket_strerror($errorcode);
			
			die("Could not send data: [$errorcode] $errormsg \n");
			
			return false;
		}

		return true;
	}
	
	public function receive_data(){
		
		//global $server, $port, $sock;
		
		$data_received = false;
		
		for ($x = 1; $x <= 5; $x++) {
			
			//if(socket_recv ( $sock , $reply , 2045 , MSG_WAITALL ) === FALSE)
			if(socket_recv ( $this->sock , $reply , 2045 , MSG_DONTWAIT ) === FALSE)
			{
				//$errorcode = socket_last_error();
				//$errormsg = socket_strerror($errorcode);
				//die("Could not receive data: [$errorcode] $errormsg \n");
				//return false;
				
				sleep(1);
			} else {
				$data_received = true;
				break;
			}

		}
		
		if(!$data_received){
			return false;
		}
			
		
		if($reply == "failed"){
			echo "Connection failed :(";
			return false;
		}			
		
		return $reply;
	}
	
	
	
}



?>