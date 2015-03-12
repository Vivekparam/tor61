var spawn = require('child_process').spawn;
var regClient = spawn('python', ['./registration_client.py',
				 '12345',
				 'foo',
				  '54321']
		     );

function endChild() {
    regClient.kill('SIGINT');
    process.exit(0);
}

regClient.stdout.on('data', function(data) {
    console.log(data.toString());
});

regClient.stderr.on('data', function(data) {
    console.log(data.toString());
});

process.stdin.on('data', function(chunk) {
    chunk = chunk.toString().trim();
    if ( chunk == 'q' ) endChild();
});

process.on('SIGINT', endChild );

// Show that we're still running while registration_client.py
// runs as child process
var timer = setInterval(function() {
    console.log("I'm still here");
}, 3000 );
