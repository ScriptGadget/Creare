
//
// As mentioned at http://en.wikipedia.org/wiki/XMLHttpRequest
//
if( !window.XMLHttpRequest ) XMLHttpRequest = function()
    {
		try{ return new ActiveXObject("Msxml2.XMLHTTP.6.0") }catch(e){}
		try{ return new ActiveXObject("Msxml2.XMLHTTP.3.0") }catch(e){}
		try{ return new ActiveXObject("Msxml2.XMLHTTP") }catch(e){}
		try{ return new ActiveXObject("Microsoft.XMLHTTP") }catch(e){}
		throw new Error("Could not find an XMLHttpRequest alternative.")
	};

//
// Makes an AJAX request to a local server function w/ optional arguments
//
// functionName: the name of the server's AJAX function to call
// opt_argv: an Array of arguments for the AJAX function
//
function Request(idempotent, function_name, opt_argv) {

	if (!opt_argv)
        opt_argv = new Array();

	// Find if the last arg is a callback function; save it
	var callback = null;
	var len = opt_argv.length;
	if (len > 0 && typeof opt_argv[len-1] == 'function') {
        callback = opt_argv[len-1];
        opt_argv.length--;
	}
	var async = (callback != null);

	// Encode the arguments in to a URI
	var query = '';
	for (var i = 0; i < opt_argv.length; i++) {
        var key = 'arg' + i;
        var val = JSON.stringify(opt_argv[i]);
        query += '&' + key + '=' + encodeURIComponent(val);
	}
	query += '&time=' + new Date().getTime(); // IE cache workaround
      
	var req = new XMLHttpRequest();
	if(idempotent){
        req.open('GET', '/'+encodeURIComponent(function_name)+'?' + query, async);
	}else{
        req.open('POST', '/'+encodeURIComponent(function_name), async);
        req.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
        req.setRequestHeader("Content-length", query.length);
        req.setRequestHeader("Connection", "close");        
	}

	if (async) {
        req.onreadystatechange = function() {
			if(req.readyState == 4 && req.status == 200) {
				var response = null;
				try {
					response = JSON.parse(req.responseText); 
				} catch (e) {
					$('alert1').innerHTML = "Error: " + req.responseText;
				}
				callback(response);
			}

			if(req.status != 200){
				$('alert1').innerHTML = "Server Error: " + req.status;
			}
        }
	}
      
	// Make the actual request
	if(idempotent){
        req.send(null);
	}else{
        req.send(query);
	}
}

// Adds a stub function that will pass the arguments to the AJAX call
function InstallFunction(obj, functionName, idempotent) {
	obj[functionName] = function() { Request(idempotent, functionName, arguments); }
}

// Server object that will contain the callable methods
var server = {};

// Handy "macro"
function $(id){
	return document.getElementById(id);
}

