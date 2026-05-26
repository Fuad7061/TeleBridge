document.addEventListener('DOMContentLoaded', function() {
  document.body.addEventListener('htmx:afterSwap', function(evt) {
    if (evt.detail.target.id === 'source-chats') {
      var select = evt.detail.target.querySelector('select');
      if (select) select.name = 'source_chat_id';
    }
  });
});
