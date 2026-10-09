name: Actualizar Datos de Viento ICON-EU

on:
  schedule:
    # Se ejecuta automáticamente cada 6 horas
    - cron: '30 */6 * * *'
  workflow_dispatch: # Permite probarlo manualmente

jobs:
  update-wind:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout del repositorio
      uses: actions/checkout@v3

    - name: Configurar Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'

    - name: Instalar librerías de sistema y Python
      run: |
        sudo apt-get update
        sudo apt-get install -y libeccodes-dev
        pip install xarray cfgrib eccodes numpy

    - name: Ejecutar script de extracción ICON-EU
      run: python generar_viento_icon.py

    - name: Guardar y hacer Commit del JSON actualizado
      run: |
        git config --global user.name 'github-actions[bot]'
        git config --global user.email 'github-actions[bot]@users.noreply.github.com'
        git add viento-espana.json
        git status
        git diff-index --quiet HEAD || (git commit -m "bot: Actualización automática viento ICON-EU" && git push)
