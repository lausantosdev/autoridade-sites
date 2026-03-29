(function() {
  'use strict';

  // Verifica se o widget está configurado
  if (!window.AUTORIDADE_WIDGET || !window.AUTORIDADE_WIDGET.workerUrl) {
    return;
  }

  const config = window.AUTORIDADE_WIDGET;

  // Estado do widget
  let currentStep = 1;
  let userName = '';
  let userWhatsApp = '';
  let targetWhatsAppUrl = '';

  // Elementos do DOM
  let overlay;
  let modal;
  let messagesContainer;
  let inputField;
  let sendButton;

  // Inicializa o widget
  function initWidget() {
    createModal();
    setupEventListeners();
    interceptWhatsAppLinks();
  }

  // Cria o modal
  function createModal() {
    overlay = document.createElement('div');
    overlay.id = 'aw-overlay';
    overlay.className = 'aw-overlay';
    overlay.style.display = 'none';

    modal = document.createElement('div');
    modal.id = 'aw-modal';
    modal.className = 'aw-modal';

    const closeButton = document.createElement('button');
    closeButton.id = 'aw-close';
    closeButton.className = 'aw-close';
    closeButton.innerHTML = '×';
    closeButton.setAttribute('aria-label', 'Fechar');

    const header = document.createElement('div');
    header.className = 'aw-header';

    const avatar = document.createElement('div');
    avatar.className = 'aw-avatar';
    avatar.innerHTML = '<i class="fab fa-whatsapp"></i>';

    const headerInfo = document.createElement('div');

    const title = document.createElement('div');
    title.className = 'aw-title';
    title.textContent = config.empresaNome || 'Atendimento';

    const status = document.createElement('div');
    status.className = 'aw-status';
    status.textContent = '● Online agora';

    headerInfo.appendChild(title);
    headerInfo.appendChild(status);

    header.appendChild(avatar);
    header.appendChild(headerInfo);

    messagesContainer = document.createElement('div');
    messagesContainer.id = 'aw-messages';
    messagesContainer.className = 'aw-messages';

    const inputArea = document.createElement('div');
    inputArea.id = 'aw-input-area';
    inputArea.className = 'aw-input-area';

    inputField = document.createElement('input');
    inputField.id = 'aw-input';
    inputField.className = 'aw-input';
    inputField.type = 'text';
    inputField.placeholder = 'Seu nome completo';

    sendButton = document.createElement('button');
    sendButton.id = 'aw-send';
    sendButton.className = 'aw-send';
    sendButton.textContent = 'Continuar →';

    inputArea.appendChild(inputField);
    inputArea.appendChild(sendButton);

    modal.appendChild(closeButton);
    modal.appendChild(header);
    modal.appendChild(messagesContainer);
    modal.appendChild(inputArea);

    overlay.appendChild(modal);
    document.body.appendChild(overlay);

    // Adiciona mensagem inicial
    addBotMessage('Olá! 👋 Para te atender melhor no WhatsApp, pode me dizer seu nome?');
  }

  // Adiciona mensagem do bot
  function addBotMessage(text) {
    const message = document.createElement('div');
    message.className = 'aw-bubble';
    message.textContent = text;
    messagesContainer.appendChild(message);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  // Configura event listeners
  function setupEventListeners() {
    // Botão de fechar
    document.getElementById('aw-close').addEventListener('click', closeModal);

    // Clique no overlay
    overlay.addEventListener('click', function(e) {
      if (e.target === overlay) {
        closeModal();
      }
    });

    // Botão de enviar
    sendButton.addEventListener('click', handleSend);

    // Tecla Enter
    inputField.addEventListener('keypress', function(e) {
      if (e.key === 'Enter') {
        handleSend();
      }
    });
  }

  // Intercepta links do WhatsApp
  // DOM já está pronto (script carrega no final do </body>)
  function interceptWhatsAppLinks() {
    const whatsappLinks = document.querySelectorAll('a[href*="wa.me"]');
    whatsappLinks.forEach(link => {
      link.addEventListener('click', function(e) {
        e.preventDefault();
        targetWhatsAppUrl = link.href;
        openModal();
      });
    });
  }

  // Abre o modal
  function openModal() {
    overlay.style.display = 'flex';
    inputField.focus();
  }

  // Fecha o modal
  function closeModal() {
    overlay.style.display = 'none';
    currentStep = 1;
    userName = '';
    userWhatsApp = '';
    messagesContainer.innerHTML = '';
    inputField.value = '';
    inputField.placeholder = 'Seu nome completo';
    sendButton.textContent = 'Continuar →';
    addBotMessage('Olá! 👋 Para te atender melhor no WhatsApp, pode me dizer seu nome?');
  }

  // Lida com o envio
  function handleSend() {
    if (currentStep === 1) {
      userName = inputField.value.trim();
      if (!userName) {
        alert('Por favor, informe seu nome.');
        return;
      }

      // Adiciona mensagem do usuário
      const userMessage = document.createElement('div');
      userMessage.className = 'aw-bubble';
      userMessage.style.alignSelf = 'flex-end';
      userMessage.style.backgroundColor = 'var(--primary)';
      userMessage.style.color = 'white';
      userMessage.textContent = userName;
      messagesContainer.appendChild(userMessage);

      // Adiciona mensagem do bot para etapa 2
      addBotMessage(`Perfeito, ${userName}! Qual é o seu WhatsApp para retorno?`);

      // Atualiza placeholder e botão
      inputField.value = '';
      inputField.placeholder = 'Ex: (11) 99999-8888';
      sendButton.textContent = 'Ir para WhatsApp →';
      currentStep = 2;
      inputField.focus();
    } else if (currentStep === 2) {
      userWhatsApp = inputField.value.trim();
      if (!userWhatsApp) {
        alert('Por favor, informe seu WhatsApp.');
        return;
      }

      // Valida WhatsApp (mínimo 8 dígitos)
      const digitsOnly = userWhatsApp.replace(/\D/g, '');
      if (digitsOnly.length < 8) {
        alert('Por favor, informe um número de WhatsApp válido.');
        return;
      }

      // Adiciona mensagem do usuário
      const userMessage = document.createElement('div');
      userMessage.className = 'aw-bubble';
      userMessage.style.alignSelf = 'flex-end';
      userMessage.style.backgroundColor = 'var(--primary)';
      userMessage.style.color = 'white';
      userMessage.textContent = userWhatsApp;
      messagesContainer.appendChild(userMessage);

      // Envia dados para o worker
      sendToWorker(userName, userWhatsApp);

      // Fecha o modal e abre o WhatsApp
      closeModal();
      window.open(targetWhatsAppUrl, '_blank');
    }
  }

  // Envia dados para o worker
  function sendToWorker(name, whatsapp) {
    fetch(config.workerUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        nome: name,
        whatsapp: whatsapp,
        dominio: config.dominio,
        pagina: window.location.href,
        keyword: config.keyword,
        local: config.local,
        client_token: config.clientToken
      })
    }).catch(() => {});
  }

  // Inicializa o widget
  initWidget();
})();