import os
import time 
import csv 
from datetime import datetime 
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
import dotenv

dotenv.load_dotenv()


# print("senha do instagram: ", os.getenv("PASSWORD"))
# Atenção: Instale as dependências: pip install -r requirements.txt

def login(driver, login_url, username, password):
    driver.get(login_url)
    try:
        # --- SELETORES ATUALIZADOS ---
        # Usando 'aria-label' que é mais estável que IDs ou classes que mudam muito.
        print("[Info] - Tentando fazer login...")

        # 1. Aguarda e preenche o campo de usuário
        seletor_usuario = '//input[@aria-label="Nome de usuário, email ou celular"]'
        campo_usuario = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, seletor_usuario))
        )
        campo_usuario.send_keys(username)

        # 2. Aguarda e preenche o campo de senha
        seletor_senha = '//input[@aria-label="Senha"]'
        campo_senha = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, seletor_senha))
        )
        campo_senha.send_keys(password)
        
        # 3. Aguarda e clica no botão "Entrar"
        # O botão pode ser um <button> ou um <div>, este seletor busca um elemento clicável com o texto "Entrar"
        seletor_botao_entrar = "//*[(@role='button' or @type='submit')][contains(., 'Entrar')]"
        botao_entrar = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, seletor_botao_entrar))
        )
        botao_entrar.click()

        # 4. Aguarda a conclusão do login e o carregamento da página principal
        print("[Info] - Login realizado com sucesso. Aguardando a página carregar...")
        time.sleep(12)# Um tempo maior para garantir que tudo carregue após o login
        try:
            print("[Info] - Verificando se há pop-ups para fechar...")
            # Usando o seletor exato do botão "Fechar" que analisamos
            seletor_botao_fechar = "//div[@role='button' and @aria-label='Fechar']"
            
            # Espera até 10 segundos para o pop-up aparecer e ser clicável
            botao_fechar = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, seletor_botao_fechar))
            )
            botao_fechar.click()
            print("[Info] - Pop-up fechado com sucesso.")
            time.sleep(2) # Pequena pausa após fechar

        except TimeoutException:
            # Se o botão "Fechar" não aparecer em 10 segundos, apenas informa e continua.
            print("[Info] - Nenhum pop-up de 'Fechar' encontrado. Continuando...")

    except TimeoutException:
        print("[ERRO] - Falha no login. Verifique se os seletores ainda são válidos ou se a página demorou muito para carregar.")
        # Salva um print da tela para ajudar a depurar o erro
        driver.save_screenshot('erro_login_screenshot.png')
        print("[Info] - Um print da tela foi salvo como 'erro_login_screenshot.png'.")
        driver.quit()
        # É importante encerrar o script se o login falhar
        raise SystemExit


def scrape_following(bot, username, user_input, termo_pesquisa):
    bot.get(f'https://www.instagram.com/{username}/')
    time.sleep(4) 
    WebDriverWait(bot, TIMEOUT).until(EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/following')]"))).click()
    
    time.sleep(3) 

    # --- MODIFICAÇÃO 1: Lidar com busca vazia ---
    # Só executa a busca se o usuário digitou algum termo.
    if termo_pesquisa and termo_pesquisa.strip():
        print(f"[Info] - Pesquisando por '{termo_pesquisa}' na lista de 'seguindo' de {username}...")
        try:
            wait = WebDriverWait(bot, 10)
            seletor_xpath_pesquisa = '//input[@aria-label="Entrada da pesquisa"]'
            campo_pesquisa = wait.until(EC.visibility_of_element_located((By.XPATH, seletor_xpath_pesquisa)))
            campo_pesquisa.clear()
            campo_pesquisa.send_keys(termo_pesquisa)
            time.sleep(3)
            print("[Info] - Iniciando a extração dos resultados filtrados...")
        except TimeoutException:
            print("[Erro] - Não foi possível encontrar o campo de pesquisa. A extração continuará sem filtro.")
    else:
        print("[Info] - Nenhum termo de pesquisa fornecido. Extraindo os primeiros da lista...")

    usuarios_coletados = set()
    nome_arquivo_csv = 'instagram_leads.csv'
    data_da_coleta = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

    while len(usuarios_coletados) < user_input:
        tamanho_anterior = len(usuarios_coletados)
        
        elementos_a = bot.find_elements(By.XPATH, '//a[@href and .//*[text()]]')
        
        novos_leads = []

        for elemento in elementos_a:
            # --- MODIFICAÇÃO 2: Respeitar o limite exato ---
            # Se o número de usuários coletados já atingiu o limite, para de procurar novos.
            if len(usuarios_coletados) >= user_input:
                break

            link = elemento.get_attribute('href')
            
            if link:
                partes_link = link.strip('/').split('/')
                if len(partes_link) == 4 and partes_link[2] == "www.instagram.com":
                    nome_usuario_extraido = partes_link[3]
                    
                    if nome_usuario_extraido not in usuarios_coletados:
                        if nome_usuario_extraido.lower() != username.lower():
                            usuarios_coletados.add(nome_usuario_extraido)
                            lead_info = [f"@{nome_usuario_extraido}", link, data_da_coleta, f"@{username}"]
                            novos_leads.append(lead_info)
        
        if novos_leads:
            try:
                arquivo_existe = os.path.exists(nome_arquivo_csv)
                with open(nome_arquivo_csv, 'a', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    if not arquivo_existe:
                        writer.writerow(['Nome', 'Link do Perfil', 'Data da Coleta', 'Perfil de Origem'])
                    writer.writerows(novos_leads)
            except Exception as e:
                print(f"[ERRO] - Falha ao salvar no arquivo CSV: {e}")

        # Se o limite foi atingido, sai do loop principal para não rolar a tela à toa.
        if len(usuarios_coletados) >= user_input:
            print(f"[Info] - Limite de {user_input} leads atingido.")
            break

        ActionChains(bot).send_keys(Keys.END).perform()
        time.sleep(2)

        if len(usuarios_coletados) == tamanho_anterior:
            if len(usuarios_coletados) < user_input and tamanho_anterior > 0:
                 print("[Info] - Não foram encontrados mais perfis novos. Finalizando busca.")
            elif tamanho_anterior == 0:
                 print("[Alerta] - Nenhum perfil foi encontrado com os critérios atuais.")
            break
            
    print(f"[SUCESSO] - Foram salvos {len(usuarios_coletados)} leads no arquivo '{nome_arquivo_csv}'.")

def scrape():
    user_input = int(input('[Required] - Quantos seguidores você deseja raspar (100-2000 recomendado): '))
    usernames = input("coloque os nomes de usuário do Instagram que você deseja raspar (separados por vírgulas): ").split(",")

    termo_pesquisa = input("[Opcional] - Insira um termo para busca (deixe em branco para pegar o primeiro da lista): ")


    # Para windows
    os.environ["webdriver.chrome.driver"] = "C:\\webdriver\\chromedriver.exe"
  
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")
    options.add_argument('--no-sandbox')
    options.add_argument("--log-level=3")
    mobile_emulation = {
        "userAgent": "Mozilla/5.0 (Linux; Android 4.2.1; en-us; Nexus 5 Build/JOP40D) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/90.0.1025.166 Mobile Safari/535.19"}
    options.add_experimental_option("mobileEmulation", mobile_emulation)

    bot = webdriver.Chrome(options=options)

    login_url = 'https://www.instagram.com/accounts/login/'
    username = "pedro_teste_1"
    password = os.getenv("PASSWORD")

    login(bot, login_url, username, password)

    for user in usernames:
        user = user.strip()
        scrape_following(bot, user, user_input, termo_pesquisa)

    bot.quit()

if __name__ == '__main__':
    TIMEOUT = 60
    scrape()
