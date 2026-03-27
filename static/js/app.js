// Formatear moneda peruana
function formatSol(n) {
  return 'S/ ' + Number(n).toLocaleString('es-PE', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
}

// Auto-dismiss alerts
document.addEventListener('DOMContentLoaded', function() {
  setTimeout(function() {
    document.querySelectorAll('.alert:not(.alert-warning)').forEach(function(a) {
      const bsAlert = new bootstrap.Alert(a);
      bsAlert.close();
    });
  }, 5000);
});
