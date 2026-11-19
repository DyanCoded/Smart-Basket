declare module 'react-native-sqlite-storage' {
  export interface ResultSetRowList {
    length: number;
    item(index: number): Record<string, unknown>;
    raw(): Record<string, unknown>[];
  }

  export interface ResultSet {
    insertId: number;
    rowsAffected: number;
    rows: ResultSetRowList;
  }

  export interface Transaction {
    executeSql(
      sqlStatement: string,
      arguments?: unknown[],
      callback?: (transaction: Transaction, resultSet: ResultSet) => void,
      errorCallback?: (transaction: Transaction, error: Error) => boolean | void
    ): void;
  }

  export interface SQLiteDatabase {
    transaction(
      scope: (tx: Transaction) => void,
      error?: (error: Error) => void,
      success?: () => void
    ): Promise<void>;
    executeSql(
      statement: string,
      params?: unknown[]
    ): Promise<[ResultSet]>;
    close(): Promise<void>;
  }

  export interface DatabaseParams {
    name: string;
    location?: 'default' | 'Library' | 'Documents';
  }

  export function enablePromise(enable: boolean): void;
  export function openDatabase(params: DatabaseParams): Promise<SQLiteDatabase>;

  const SQLite: {
    enablePromise: typeof enablePromise;
    openDatabase: typeof openDatabase;
  };

  export default SQLite;
}
