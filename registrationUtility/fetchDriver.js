var spawn = require('child_process').spawn;

if ( process.argv.length != 3 ) {
    console.log("Usage: node fetchDriver.js <namestring>");
    process.exit(1);
}

var namestring = process.argv[2];
var allData = '';

var fetchClient = spawn('python', ['./fetch.py',
                                  namestring,
				]
		     );

fetchClient.stdout.on('data', function(data) {
    allData += data;
});

fetchClient.stdout.on('end', function() {
    var entries = allData.split("\n");
    // After the split, the last entry is always empty
    for (var i = 0; i < entries.length-1; i++ ) {
        console.log('Read: "' + entries[i] + '"');
    }
    process.exit(0);
});

fetchClient.stderr.on('data', function(data) {
    console.log(data.toString());
});

process.stdin.on('data', function(chunk) {
    chunk = chunk.toString().trim();
    if ( chunk == 'q' ) process.exit(0);
});
