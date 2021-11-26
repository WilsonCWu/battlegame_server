$(function() {
    $('#datatable').bootstrapTable({
      striped: true,
      pagination: true,
      showColumns: true,
      showToggle: true,
      showExport: true,
      sortable: true,
      paginationVAlign: 'both',
      pageSize: 'All',
      pageList: [10, 25, 50, 100, 'ALL'],
      columns: JSON.parse(document.getElementById('columns_imported').textContent),  // here is where we use the column content from our Django View
      data: JSON.parse(document.getElementById('data_imported').textContent), // here is where we use the data content from our Django View. we escape the content with the safe tag so the raw JSON isn't shown.
    });
  });