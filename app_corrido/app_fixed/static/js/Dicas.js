/* Parte da tela de Dicas Sustentáveis */
 
function abrirConteudo(id) {
 
    // Fecha todos os conteúdos
    const todosConteudos = document.querySelectorAll(".conteudo");
 
    todosConteudos.forEach((item) => {
 
        // Fecha os outros conteúdos
        if (item.id !== id) {
            item.classList.remove("ativo");
        }
 
    });
 
    // Abre ou fecha o conteúdo clicado
    const conteudo = document.getElementById(id);
 
    conteudo.classList.toggle("ativo");
}