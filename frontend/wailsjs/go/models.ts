export namespace backend {
	
	export class FileInfoExtended {
	    name: string;
	    fullPath: string;
	    size: number;
	    extension: string;
	    hasBOM: boolean;
	    encodingGuess: string;
	
	    static createFrom(source: any = {}) {
	        return new FileInfoExtended(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.name = source["name"];
	        this.fullPath = source["fullPath"];
	        this.size = source["size"];
	        this.extension = source["extension"];
	        this.hasBOM = source["hasBOM"];
	        this.encodingGuess = source["encodingGuess"];
	    }
	}

}

export namespace main {
	
	export class ProgressInfo {
	    downloaded: number;
	    total: number;
	    speed: number;
	    percentage: number;
	
	    static createFrom(source: any = {}) {
	        return new ProgressInfo(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.downloaded = source["downloaded"];
	        this.total = source["total"];
	        this.speed = source["speed"];
	        this.percentage = source["percentage"];
	    }
	}
	export class ScriptInfo {
	    totalTasks: number;
	    totalFiles: number;
	
	    static createFrom(source: any = {}) {
	        return new ScriptInfo(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.totalTasks = source["totalTasks"];
	        this.totalFiles = source["totalFiles"];
	    }
	}
	export class Settings {
	    concurrent: number;
	    downloadPath: string;
	
	    static createFrom(source: any = {}) {
	        return new Settings(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.concurrent = source["concurrent"];
	        this.downloadPath = source["downloadPath"];
	    }
	}
	export class TaskDisplay {
	    taskId: string;
	    taskName: string;
	    fileCount: number;
	
	    static createFrom(source: any = {}) {
	        return new TaskDisplay(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.taskId = source["taskId"];
	        this.taskName = source["taskName"];
	        this.fileCount = source["fileCount"];
	    }
	}

}

