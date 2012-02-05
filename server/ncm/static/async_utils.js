//  Copyright 2011 Bill Glover
//
//  This file is part of Creare.
//
//  Creare is free software: you can redistribute it and/or modify it
//  under the terms of the GNU General Public License as published by
//  the Free Software Foundation, either version 3 of the License, or
//  (at your option) any later version.
//
//  Creare is distributed in the hope that it will be useful, but
//  WITHOUT ANY WARRANTY; without even the implied warranty of
//  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
//  General Public License for more details.
//
//  You should have received a copy of the GNU General Public License
//  along with Creare.  If not, see <http://www.gnu.org/licenses/>.
//

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
        req.open('GET', '/rpc/'+encodeURIComponent(function_name)+'?' + query, async);
	}else{
        req.open('POST', '/rpc/'+encodeURIComponent(function_name), async);
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
					$('alert1').innerHTML = "Error: " + e + req.responseText;
				}
				if ('alert1' in response){
					$('alert1').innerHTML = response['alert1'];
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

function hideOrShow(panel, control){
	if($(panel).style.display=="block"){
		$(control).innerHTML="[show]";
		$(panel).style.display="none";
	}else{
		$(control).innerHTML="[hide]";
		$(panel).style.display="block";
	}
}

function afu_buildInput(type, name, value)
{
	input = document.createElement('input');
	input.type = type;
	input.name = name;
	input.value = value;
	return input;
}

function ajaxFileUpload(upload_field, preview, iframe)
{
	// Checking file type
	var re_text = /\.jpg|\.png|\.jpeg/i;
	var filename = upload_field.value;
	if (filename.search(re_text) == -1) {
		alert("File should be either jpg or png or jpeg");
		upload_field.form.reset();
		return false;
	}
	document.getElementById(preview).innerHTML = '<img src="/static/images/loading.gif" border="0" />';
	upload_field.form.action = '/image/upload';
	upload_field.form.target = iframe;
	upload_field.form.submit();
	upload_field.form.action = '';
	upload_field.form.target = '';
	return true;
}

function buildImageUploadForm(panel, iframe_name, form_name, parent_form_name, image_name, error_name, preview_name, preview_content, width, height)
{
	iframe = document.createElement('iframe');
	iframe.name = iframe_name;
	iframe.id = iframe_name;
	iframe.style.display = "none";
	panel.appendChild(iframe);

	preview = document.createElement('div');
	preview.id = preview_name;
	preview.innerHTML = preview_content;
	panel.appendChild(preview);

	form = document.createElement('form');
	form.name = form_name;
	form.method = "post";
	form.autocomplete = "off";
	form.enctype = "multipart/form-data";

	prompt = document.createElement('span');
	prompt.innerHTML = "Upload Picture :  (PNG or JPG " + width + "wx" + height + "h, less than 1MB)";
	form.appendChild(prompt);

	file_input = document.createElement('input');
	file_input.type = "file";
	file_input.name = "img";
	file_input.id = "picture";
	file_input.onchange = function(){return ajaxFileUpload(this, preview_name, iframe_name);};
	form.appendChild(file_input);

	form.appendChild(afu_buildInput("hidden", "parent_form", "product_form"));
	form.appendChild(afu_buildInput("hidden", "max_width", width));
	form.appendChild(afu_buildInput("hidden", "max_height", height));
	form.appendChild(afu_buildInput("hidden", "image_field", image_name));
	form.appendChild(afu_buildInput("hidden", "error", error_name));
	form.appendChild(afu_buildInput("hidden", "preview", preview_name));
	
	error = document.createElement('span');
	error.id = error_name;
	form.appendChild(error);

	panel.appendChild(form);
}