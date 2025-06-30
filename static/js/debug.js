// Debug script to catch syntax errors
window.addEventListener('error', function(e) {
    console.error('Global error caught:', {
        message: e.message,
        filename: e.filename,
        lineno: e.lineno,
        colno: e.colno,
        error: e.error
    });
});

console.log('Debug script loaded - monitoring for errors...');