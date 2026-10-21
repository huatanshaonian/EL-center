file(GLOB SRCS "*.c")
idf_component_register(SRCS ${SRCS}
                       INCLUDE_DIRS "."
                       PRIV_REQUIRES nvs_flash esp_driver_gpio esp_driver_spi esp_driver_ledc esp_driver_pcnt
                                     esp_driver_gptimer esp_driver_i2c esp_driver_uart esp_timer esp_wifi
                                     esp_netif esp_event lwip esp_system esp_http_server esp_http_client
                                     esp-tls mbedtls app_update json
                       EMBED_TXTFILES "www/index.html")
# S1/S3：panic 时先把高压、IV-18 关掉（见 safety.c）
target_link_libraries(${COMPONENT_LIB} INTERFACE "-Wl,--wrap=esp_panic_handler")
