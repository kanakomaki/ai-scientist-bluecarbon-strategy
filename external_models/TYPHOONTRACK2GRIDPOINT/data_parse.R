library(dplyr)
library(stringr)

# ファイル読み込み　（ソース：https://www.jma.go.jp/jma/jma-eng/jma-center/rsmc-hp-pub-eg/besttrack.html）
lines <- readLines("bst_all.txt")  # ←ファイルパス

# 初期化
all_records <- list()

i <- 1
while (i <= length(lines)) {
  
  line <- lines[i]
  
if (startsWith(line, "66666")) {
  # ヘッダー行
  parts <- str_split_fixed(str_squish(line), " ", n = 8)  # これはnum_linesだけ取るために残す
  cyclone_id <- parts[2]
  num_lines <- as.integer(parts[3])
  
  # 台風名は41文字目から60文字目をsubstrで取る
  cyclone_name <- str_trim(substr(line, 41, 60))

  if (cyclone_name == "") cyclone_name <- NA

    # 次の行からデータ行
    for (j in 1:num_lines) {
      data_line <- lines[i + j]

      # 文字列で分割
      windspeed_str <- substr(data_line, 34, 36)
      windspeed_kt <- as.numeric(str_trim(windspeed_str))
      #print(windspeed_kt)      

      # データ行も空白で分割
      data_parts <- str_split_fixed(str_squish(data_line), " ", n = 12)
      
      raw_datetime <- data_parts[1]  # 8桁：YYMMDDHH
      # 年の部分を補完する
      yy <- as.integer(substr(raw_datetime, 1, 2))
      if (yy >= 50) {
        yyyy <- 1900 + yy
      } else {
        yyyy <- 2000 + yy
      }
      mmddhh <- substr(raw_datetime, 3, 8)
      datetime <- paste0(yyyy, mmddhh)  # これでYYYYMMDDHHになる

      grade <- data_parts[3]
      lat <- as.numeric(data_parts[4]) / 10
      lon <- as.numeric(data_parts[5]) / 10
      pressure <- as.numeric(data_parts[6])
      #windspeed_ms <- windspeed_kt * 0.51444
      
#       # データを保存
#       record <- data.frame(
#         cyclone_id = cyclone_id,
#         cyclone_name = cyclone_name,
#         datetime = datetime,
#         lat = lat,
#         lon = lon,
#         pressure = pressure,
#         windspeed = windspeed_kt,
#         stringsAsFactors = FALSE
#       )
      record <- data.frame(
        BASIN = "WP",
        CY = "",
        YYYYMMDDHH = datetime,
        LAT = lat,
        LON = lon,
        VMAX = windspeed_kt,
        STORMNAME = cyclone_name,
        stringsAsFactors = FALSE
      )
      
      all_records <- append(all_records, list(record))
    }
    
    # 次のヘッダー行へ
    i <- i + num_lines
  }
  
  i <- i + 1
}

# 全データを結合
final_df <- bind_rows(all_records)

# # 日付フォーマットを整える
# final_df$datetime <- as.POSIXct(final_df$datetime, format = "%y%m%d%H", tz = "UTC")

# 列順も合わせて
final_df <- final_df %>% select(BASIN, CY, YYYYMMDDHH, LAT, LON, VMAX, STORMNAME)

# 結果確認
print(head(final_df))
write.csv(final_df, "parsed_typhoon_data.csv", row.names = FALSE)







