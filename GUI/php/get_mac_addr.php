<?php

function get_mac_address($ip_addr) {

	exec("/usr/sbin/arp -a " . $ip_addr, $output, $return);

	$mac_addr = explode(' ', $output[0], 5);
	$mac_addr = $mac_addr[3];

	if($mac_addr == "entries"){
		return NULL;
	}
		
	return $mac_addr;
}

?>

