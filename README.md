# 🛠️ Logbook de Manutenção e Alertas - Voz Do Condutor (VDC)

Este repositório contém o código-fonte da ferramenta de **Registo de Manutenção e Alertas** (Logbook Digital) desenvolvida para a comunidade de motoristas TVDE da **Voz do Condutor (VDC)**.

A ferramenta foi concebida para ajudar os motoristas a gerir os custos, a quilometragem e o tempo das intervenções dos seus veículos, garantindo que nunca perdem os prazos críticos de manutenção ou inspeção.

---

## 💡 Sobre o Projeto

O Logbook funciona como um sistema de gestão de ativos, permitindo:

* **Registo Completo:** Guardar data, KM e custo de cada intervenção (troca de óleo, pneus, inspeções, etc.).
* **Alertas Automáticos:** Calcular e exibir alertas urgentes baseados em regras de KM (ex: trocar o óleo a cada 15.000 km) ou tempo (ex: Inspeção anualmente).
* **Análise de Custos:** Gerar um relatório PDF com gráficos para análise mensal dos custos de manutenção.

**Atenção:** Esta aplicação é executada através de um servidor Python local (Flask) e não funciona apenas abrindo o ficheiro HTML no navegador.

---

## 🚀 Como Usar e Executar a Aplicação (Passo a Passo)

Para aceder ao *dashboard* e usar todas as funcionalidades (incluindo a geração de PDF), precisa de executar o servidor web no seu computador.

### 1. Requisitos

Certifique-se de que tem o **Python** (versão 3.8 ou superior) instalado no seu sistema.

### 2. Preparar o Ambiente

Abra a **Linha de Comandos** (Terminal ou CMD) e instale as bibliotecas Python necessárias (Flask, pandas, etc.).

```bash
pip install Flask pandas matplotlib reportlab
