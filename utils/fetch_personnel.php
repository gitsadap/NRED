<?php
header('Content-Type: application/json');

$host = "10.10.58.16";
$user = "gitsadap";
$pw = "it[[{ko-hv,^]8ItgdK9i";
$dbname = "db_user";

// Simple Logger stub if not exists
if (!class_exists('Logger')) {
    class Logger {
        public static function logError($msg, $file, $line) {
            error_log("Error: $msg in $file on line $line");
        }
    }
}

$c = mysqli_connect($host, $user, $pw, $dbname);
if (!$c) {
    Logger::logError('Database connection failed: ' . mysqli_connect_error(), __FILE__, __LINE__);
    echo json_encode(['status' => 'error', 'message' => 'เชื่อมต่อฐานข้อมูลไม่สำเร็จ']);
    exit;
}
mysqli_set_charset($c, "utf8");

// TODO: Verify the table name. Assuming 'users' or 'personnel' based on DB name 'db_user'.
// TODO: Verify the column name for department. Assuming 'department' or 'dept_name'.
$table_name = "user"; // Replace with actual table name if different
$dept_column = "department"; // Replace with actual column name

$target_dept = "ภาควิชาทรัพยากรธรรมชาติเเละสิ่งเเวดล้อม";

$sql = "SELECT * FROM $table_name WHERE $dept_column = '" . mysqli_real_escape_string($c, $target_dept) . "'";
$result = mysqli_query($c, $sql);

if ($result) {
    $data = [];
    while ($row = mysqli_fetch_assoc($result)) {
        $data[] = $row;
    }
    echo json_encode(['status' => 'success', 'count' => count($data), 'data' => $data], JSON_UNESCAPED_UNICODE);
} else {
    Logger::logError('Query failed: ' . mysqli_error($c), __FILE__, __LINE__);
    echo json_encode(['status' => 'error', 'message' => 'เกิดข้อผิดพลาดในการดึงข้อมูล: ' . mysqli_error($c)]);
}

mysqli_close($c);
?>
